"""Measured CPU/RAM software performance for the zero-neural MICRO-RAG baseline.

This is not an LLM inference, ONNX quantization, or independent benchmark. The
same visible fictional fixture is used for every policy, with warm start
effects and all corpus data held in memory. Run on real target hardware for
meaningful optimization claims.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import statistics
import sys
import time
from pathlib import Path

from raglab.micro_v02.__main__ import _load_json, load_documents
from raglab.micro_v02.pipeline import MicroRAG
from raglab.micro_v02.evaluation import evaluate_cases, write_json


def _rss_bytes() -> int | None:
    try:
        import resource
    except ImportError:
        return None
    rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(rss if sys.platform=="darwin" else rss*1024)


def quantile(sorted_values: list[float], fraction: float) -> float:
    import math
    if not sorted_values:
        raise ValueError("Cannot compute quantile of empty samples")
    return sorted_values[min(len(sorted_values)-1,max(0,math.ceil(fraction*len(sorted_values))-1))]


def benchmark(
    documents: list, cases: list[dict],
    *,
    top_ks: tuple[int,...] = (1,3),
    iterations: int = 30,
) -> dict:
    if not (1 <= iterations <= 300):
        raise ValueError("Bounded iteration count must be 1..300")
    if not top_ks or any(k <= 0 for k in top_ks):
        raise ValueError("All K values must be positive")
    if not cases or len(cases)>1000:
        raise ValueError("At most 1,000 QA cases are supported")
    configs=[]
    for k in top_ks:
        started=time.perf_counter()
        rag=MicroRAG(documents,top_k=k)
        index_ms=(time.perf_counter()-started)*1000
        for row in cases:
            rag.answer(row["question"]) # warmup excluded from measured samples
        times=[]
        calls=0
        for _ in range(iterations):
            for row in cases:
                start=time.perf_counter()
                result=rag.answer(row["question"])
                times.append((time.perf_counter()-start)*1000)
                calls+=result.read_calls
        times.sort()
        evaluated=evaluate_cases(rag,cases)
        configs.append({
            "top_k":k,
            "index_construction_ms":index_ms,
            "sample_count":len(times),
            "wall_ms":{
                "mean":statistics.mean(times),
                "p50":statistics.median(times),
                "p95":quantile(times,0.95),
                "max":max(times),
            },
            "total_reader_calls":calls,
            "mean_reader_calls_per_question":calls/len(times),
            "strict_correct_visible_fixture":evaluated["strict_correct"],
            "wrong_accepts_visible_fixture":evaluated["wrong_accepts"],
            "fixture_cases":evaluated["n"],
        })
    return {
        "experiment":"MICRO_V02_ZERO_NEURAL_SOFTWARE_CPU_PROFILE",
        "status":"VISIBLE_SYNTHETIC_ENGINEERING_PROFILE_NOT_SCIENTIFIC_EFFICIENCY_PROOF",
        "model_calls":0,
        "source_count":len(documents),
        "fixture_cases":len(cases),
        "iterations":iterations,
        "environment":{
            "python":platform.python_version(),
            "platform":platform.platform(),
            "cpu_count":os.cpu_count(),
            "peak_process_rss_bytes_after_all_variants":_rss_bytes(),
            "github_sha":os.getenv("GITHUB_SHA"),
        },
        "configurations":configs,
        "limitations":[
            "All data are visible fictional source:value records designed for this software",
            "No neural model was used; these are CPU retrieval/parse/decision costs only",
            "Warm-start sequential variants on one machine; relative timings not controlled CPU inference comparisons",
            "Process RSS is a cumulative high-water mark, not independent per-policy RSS",
            "No energy, cold model startup, nonstructured document QA or independent source-supported benchmark",
            "This study cannot substitute for quantized ONNX vs FP32 model parity tests",
        ],
    }


def main() -> None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--documents",required=True)
    p.add_argument("--cases",required=True)
    p.add_argument("--output",required=True)
    p.add_argument("--iterations",type=int,default=30)
    p.add_argument("--top-k",type=int,nargs="+",default=[1,3])
    args=p.parse_args()
    docs=load_documents(args.documents)
    cases=_load_json(args.cases)
    if not isinstance(cases,list):
        raise ValueError("Case fixture must be a JSON array")
    result=benchmark(docs,cases,top_ks=tuple(args.top_k),iterations=args.iterations)
    write_json(Path(args.output),result)
    print(json.dumps({
        "experiment":result["experiment"],"status":result["status"],
        "configurations":result["configurations"],
    },sort_keys=True))


if __name__=="__main__":
    main()
