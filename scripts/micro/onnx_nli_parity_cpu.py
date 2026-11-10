"""M5: published AVX2-INT8 ONNX vs FP32 PyTorch *same* NLI checkpoint.

The quantized ONNX file is supplied by its original publisher. The comparison
is run on the same external Ragability 318-pair set and frozen inference method;
score/latency differences are observed, never assumed to be improvements.
This is verifier-only CPU inference, NOT end-to-end RAG or energy efficiency.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import statistics
import sys
import time
from pathlib import Path

import numpy as np

from raglab.evaluation.ragability_conflict import (
    DATASET_ID, DATASET_FILE, DATASET_REVISION, DATASET_LICENSE,
    read_ragability_tsv, build_conflict_pairs, score_model_rows, write_json,
)
from ragability_nli_cpu import (
    MODEL_SPECS, _license_from_info, _download_model, _load_model,
    _predict_bidirectional,
)

MODEL_KEY="deberta_xsmall"
ONNX_NAME="onnx/model_quint8_avx2.onnx"
SOURCE_DATA_SHA="e973f5ac7b4881e2cafe23f39b837643878ea6afdb769d9afa30ff66e93c8285"
# First actual CPU run freezes and reports the published checkpoint's ONNX
# weight hash. Never use floating model branches.
ONNX_WEIGHT_SHA = "21b14751a95520953bfcc607ceeb617de7cbeaeb6d60f4c8966716c743985337"


def sha_file(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as inp:
        for chunk in iter(lambda: inp.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()


from raglab.evaluation.onnx_parity import infer_onnx, compare_predictions


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output-dir",required=True)
    p.add_argument("--batch-size",type=int,default=16)
    args=p.parse_args()
    if not 1<=args.batch_size<=32:
        raise ValueError("Bounded pair batch must be 1..32")
    out=Path(args.output_dir).resolve()
    out.mkdir(parents=True,exist_ok=True)
    os.environ["TOKENIZERS_PARALLELISM"]="false"
    os.environ["OMP_NUM_THREADS"]="2"
    os.environ["MKL_NUM_THREADS"]="2"

    import torch
    import onnxruntime as ort
    from huggingface_hub import HfApi,hf_hub_download

    torch.set_num_threads(2)
    data_path=Path(hf_hub_download(
        repo_id=DATASET_ID,repo_type="dataset",filename=DATASET_FILE,
        revision=DATASET_REVISION,cache_dir=str(out/".dataset-cache"),
    ))
    if sha_file(data_path)!=SOURCE_DATA_SHA:
        raise ValueError("External benchmark source checksum changed")
    dataset_card=HfApi().dataset_info(DATASET_ID,revision=DATASET_REVISION)
    if _license_from_info(dataset_card)!=DATASET_LICENSE:
        raise ValueError("Data license metadata changed")

    rows=read_ragability_tsv(data_path)
    pairs=build_conflict_pairs(rows)
    source_pairs=[(case.premise,case.hypothesis) for case in pairs]
    spec=MODEL_SPECS[MODEL_KEY]
    model_dir=out/"weights"
    source=_download_model(spec,model_dir)
    fp_revision=source["revision"]
    onnx_file=Path(hf_hub_download(
        repo_id=spec["id"],filename=ONNX_NAME,revision=fp_revision,
        cache_dir=str(out/".model-cache"),
    ))
    onnx_sha=sha_file(onnx_file)
    if onnx_sha != ONNX_WEIGHT_SHA:
        raise ValueError("Pinned quantized ONNX SHA256 differs from verified source")

    os.environ["HF_HUB_OFFLINE"]="1"
    os.environ["TRANSFORMERS_OFFLINE"]="1"
    tokenizer,model,details=_load_model(model_dir,spec)
    source.update(details)
    from ragability_nli_cpu import _run_sanity_controls
    sanity=_run_sanity_controls(tokenizer,model)

    # Both inference backends run in one process and may benefit differently
    # from warm caches. RSS high water is shared, NOT per-backend memory.
    fp_fwd,fp_rev,fp_cost=_predict_bidirectional(
        tokenizer,model,source_pairs,batch_size=args.batch_size
    )
    del model
    opts=ort.SessionOptions()
    opts.intra_op_num_threads=2
    opts.inter_op_num_threads=1
    # A single CPU process compares both execution paths. We explicitly
    # report process high-water RSS as shared, not per-backend consumption.
    session=ort.InferenceSession(
        str(onnx_file),sess_options=opts,providers=["CPUExecutionProvider"]
    )
    providers=session.get_providers()
    if providers!=["CPUExecutionProvider"]:
        raise ValueError("ONNX must use CPUExecutionProvider only")
    # Warm the ONNX path with exactly one real batch; first-run graph
    # initialization is excluded on both paths (the FP32 sanity controls
    # above already warmed the PyTorch model).
    infer_onnx(session,tokenizer,source_pairs[:args.batch_size],batch_size=args.batch_size)
    onnx_fwd,onnx_rev,onnx_cost=infer_onnx(
        session,tokenizer,source_pairs,batch_size=args.batch_size
    )
    if fp_cost["directional_pair_inputs"] != onnx_cost["directional_inputs"]:
        raise ValueError("FP32 and ONNX executed different NLI input counts")
    fp_metrics=score_model_rows(pairs,fp_fwd,fp_rev)
    q_metrics=score_model_rows(pairs,onnx_fwd,onnx_rev)
    quality=compare_predictions(
        {"evaluation":fp_metrics},{"evaluation":q_metrics}
    )
    import resource
    rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    output={
        "experiment":"MICRO_RAG_V02_DEBERTA_INT8_ONNX_PARITY",
        "status":"REAL_CPU_PUBLIC_PAIRWISE_NLI_ONLY_NOT_FULL_RAG",
        "dataset":{
            "id":DATASET_ID,"revision":DATASET_REVISION,
            "sha256":SOURCE_DATA_SHA,"rows":53,"pair_cases":318,
            "source_groups":43,"license":DATASET_LICENSE,
        },
        "checkpoint":source,
        "onnx":{
            "file":ONNX_NAME,"revision":fp_revision,
            "sha256":onnx_sha,
            "size_bytes":onnx_file.stat().st_size,
            "providers":providers,
            "onnxruntime_version":ort.__version__,
        },
        "fp32":{
            "metrics":fp_metrics["metrics"],
            "cost":fp_cost,
            "cases":fp_metrics["cases"],
        },
        "int8":{
            "metrics":q_metrics["metrics"],
            "cost":onnx_cost,
            "cases":q_metrics["cases"],
        },
        "quality":quality,
        "sanity":sanity,
        "environment":{
            "python":platform.python_version(),"pytorch":torch.__version__,
            "os":platform.platform(),"cpu_threads":2,
            "whole_process_peak_rss_bytes":rss*1024,
            "github_sha":os.getenv("GITHUB_SHA"),
        },
        "limitations":[
            "Uses small public Ragability benchmark, not blind independent holdout",
            "Only external pairwise NLI, not end-to-end RAG answer correctness",
            "Same process shared peak RSS, not isolated per-backend memory costs",
            "Published ONNX quantization is an existing external export, not our invention",
            "No energy measurements, training parity or calibrated factual reliability",
            "Both backends are run sequentially, in one process and in fixed FP32-to-INT8 order",
            "FP32 model used generic sanity-case warmup; ONNX model used one candidate batch warmup",
            "Published AVX2-export format may run on different CPUs but no per-instruction-set speedups are guaranteed",
            "Quality parity thresholds are engineering preferences, not statistical safety gates",
        ],
    }
    write_json(out/"int8_onnx_parity.json",output)
    print(json.dumps({
        "status":output["status"],"quality":quality,
        "weights_fp32_bytes":source["weight_bytes"],
        "weights_int8_onnx_bytes":output["onnx"]["size_bytes"],
        "fp32_cpu_ms":fp_cost["total_batch_wall_ms"],
        "int8_cpu_ms":onnx_cost["total_batch_wall_ms"],
        "onnx_sha256":onnx_sha,
    },sort_keys=True))


if __name__=="__main__":
    main()
