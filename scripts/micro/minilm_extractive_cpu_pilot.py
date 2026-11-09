"""Task-matched 33M extractive QA baseline: real official SQuAD2 DEV on CPU.

deepset/minilm-uncased-squad2 (33.4M params) is TRAINED ON SQuAD 2.0.
Thus reference outcomes against public SQuAD DEV are task-matched diagnostics
and fundamentally not fair claims of superiority over untrained Pythia-14M or
general small-model RAG. The CC BY 4.0 checkpoint is only downloaded locally;
its weights and the CC BY-SA 4.0 source corpus are NEVER redistributed.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import resource
import time
from pathlib import Path
from statistics import mean

from raglab.retrieval import BM25Retriever
from raglab.micro.extractive_reader import ExtractivePrediction, decode_qa_span
from raglab.micro.squad_benchmark import load_official_squad_dev
from raglab.micro.squad_metrics import score_prediction

from squad2_natural_cpu_pilot import (
    _file_hash, _write, download_public_dev,
)

SOURCE = "deepset/minilm-uncased-squad2"
# Pinned after verified first real CPU run #42699698248. Re-run the exact
# official checkpoint; no floating main branch in published experiments.
MODEL_REVISION: str | None = "934656cdda79824eabf503ed56e15c01ddbdbe3f"
EXPECTED_LICENSE = "cc-by-4.0"
MODES = ("bm25_top1", "bm25_top5", "oracle_original_paragraph")


def download_reader(path: Path) -> dict:
    from huggingface_hub import HfApi, snapshot_download

    info = HfApi().model_info(SOURCE, revision=MODEL_REVISION or "main")
    sha = str(info.sha)
    if MODEL_REVISION and sha != MODEL_REVISION:
        raise ValueError("Reader revision mismatch")
    card = info.card_data
    license_id = (
        card.get("license", "") if isinstance(card, dict)
        else getattr(card, "license", "")
    )
    if license_id != EXPECTED_LICENSE:
        raise ValueError(f"Reader license metadata unexpectedly changed: {license_id}")
    snapshot_download(
        repo_id=SOURCE, revision=sha, local_dir=str(path),
        allow_patterns=(
            "config.json", "model.safetensors", "model-*.safetensors",
            "model.safetensors.index.json", "tokenizer_config.json",
            "special_tokens_map.json", "tokenizer.json", "vocab.txt",
        ),
        ignore_patterns=("*.bin", "*.pt", "*.py", "*.msgpack"),
    )
    safes = sorted(path.glob("*.safetensors"))
    if not safes or sum(f.stat().st_size for f in safes) > 250_000_000:
        raise ValueError("No verified-size safetensors obtained")
    return {
        "id": SOURCE, "revision": sha,
        "license": license_id,
        "weights": {
            f.name: {"bytes": f.stat().st_size, "sha256": _file_hash(f)}
            for f in safes
        },
        "trained_on": "SQuAD 2.0 (according to model card)",
        "model_card": "https://huggingface.co/deepset/minilm-uncased-squad2",
    }


class SmallExtractiveReader:
    def __init__(self, path: Path) -> None:
        from transformers import AutoModelForQuestionAnswering, AutoTokenizer

        self.tokenizer = AutoTokenizer.from_pretrained(
            str(path), local_files_only=True, use_fast=True
        )
        if not self.tokenizer.is_fast:
            raise ValueError("Fast tokenizer required for exact original offsets")
        self.model = AutoModelForQuestionAnswering.from_pretrained(
            str(path), local_files_only=True, use_safetensors=True
        )
        self.model.eval()

    def read(self, question: str, paragraph: str) -> tuple[ExtractivePrediction, int, float]:
        import torch

        t0 = time.perf_counter()
        batch = self.tokenizer(
            question, paragraph,
            truncation="only_second", max_length=384,
            return_offsets_mapping=True, return_tensors="pt",
        )
        sequence_ids = batch.sequence_ids(0)
        offsets = [tuple(int(x) for x in pair) for pair in batch["offset_mapping"][0].tolist()]
        tokens = int(batch["input_ids"].shape[1])
        del batch["offset_mapping"]
        with torch.inference_mode():
            logits = self.model(**batch)
        cls_id = self.tokenizer.cls_token_id
        cls_pos = int((batch["input_ids"][0] == cls_id).nonzero()[0].item())
        pred = decode_qa_span(
            context=paragraph,
            offsets=offsets, sequence_ids=sequence_ids,
            start_logits=logits.start_logits[0].tolist(),
            end_logits=logits.end_logits[0].tolist(),
            cls_index=cls_pos,
            threshold=0.0,
            max_answer_tokens=25,
        )
        return pred, tokens, (time.perf_counter() - t0) * 1000


def evaluate(
    *, data_path: Path, model_path: Path,
    max_cases: int, distractors: int,
) -> tuple[dict, dict]:
    benchmark = load_official_squad_dev(
        data_path, max_cases=max_cases, distractors=distractors
    )
    reader = SmallExtractiveReader(model_path)
    # Controlled warm-up with a toy unrelated to SQuAD.
    warmup = reader.read("What fruit is described?", "A ripe pear is green.")
    retriever = BM25Retriever()
    retriever.index(benchmark.dataset.documents)
    by_id = {doc.id: doc for doc in benchmark.dataset.documents}
    rows = []
    for case in benchmark.dataset.cases:
        ref = benchmark.references[case.case_id]
        t0 = time.perf_counter()
        retrieved = retriever.retrieve(case.question, 5)
        search_ms = (time.perf_counter() - t0) * 1000
        sources = {
            "bm25_top1": [retrieved[0].doc_id] if retrieved else [],
            "bm25_top5": [r.doc_id for r in retrieved],
            "oracle_original_paragraph": [ref.gold_doc_id],
        }
        for mode in MODES:
            scores = []
            for doc_id in sources[mode]:
                doc = by_id[doc_id]
                pred, inputs, elapsed_ms = reader.read(case.question, doc.text)
                if pred.answered:
                    assert pred.start is not None and pred.end is not None
                    if doc.text[pred.start:pred.end] != pred.text:
                        raise RuntimeError("Extractive output is not an exact source slice")
                scores.append((pred.logit_margin, doc_id, pred, inputs, elapsed_ms))
            # A frozen max-positive-margin top-k policy, not calibrated across
            # passages: testing more passages increases false-positive risk.
            best = max(scores, key=lambda item: item[0]) if scores else None
            if best is None or best[0] <= 0 or not best[2].answered:
                answer = "INSUFFICIENT_EVIDENCE"
                selected_doc = None
                start, end = None, None
                decision_margin = best[0] if best else None
            else:
                margin, selected_doc, prediction, _, _ = best
                answer = prediction.text
                start, end = prediction.start, prediction.end
                decision_margin = margin
            metric = score_prediction(
                answer, ref.answers, generation_status="draft_unverified"
            )
            item = {
                "case_id": case.case_id,
                "article_group": ref.official_title,
                "mode": mode,
                "answerable_original_paragraph": ref.answerable,
                "reference_em": metric["reference_em"],
                "reference_f1": metric["reference_f1"],
                "abstained": metric["abstained"],
                "answer": answer,
                "retrieved_docs": sources[mode],
                "gold_doc_in_candidates": ref.gold_doc_id in sources[mode],
                "selected_source_doc_id": selected_doc,
                "selected_source_start": start,
                "selected_source_end": end,
                "source_exact_copy": (
                    selected_doc is not None
                    and by_id[selected_doc].text[start:end] == answer
                ),
                "null_margin_max_over_passages": decision_margin,
                "model_input_tokens_all_candidates": sum(x[3] for x in scores),
                "model_cpu_forward_ms_all_candidates": sum(x[4] for x in scores),
                "bm25_shared_retrieval_ms": (
                    0.0 if mode == "oracle_original_paragraph" else search_ms
                ),
                "candidate_count": len(scores),
                "oracle_used": mode == "oracle_original_paragraph",
            }
            rows.append(item)
    by_mode = {}
    for mode in MODES:
        selected = [r for r in rows if r["mode"] == mode]
        positive = [r for r in selected if r["answerable_original_paragraph"]]
        negative = [r for r in selected if not r["answerable_original_paragraph"]]
        by_mode[mode] = {
            "n": len(selected),
            "reference_em": mean([r["reference_em"] for r in selected]),
            "reference_f1": mean([r["reference_f1"] for r in selected]),
            "answerable_exact_matches": int(sum(r["reference_em"] for r in positive)),
            "answerable_n": len(positive),
            "original_paragraph_no_answer_correct_refusals": int(
                sum(r["reference_em"] for r in negative)
            ),
            "original_paragraph_no_answer_n": len(negative),
            "gold_doc_in_candidates_for_answerable": int(sum(
                r["gold_doc_in_candidates"] for r in positive
            )),
            "source_exact_copy_count": sum(r["source_exact_copy"] for r in selected),
            "mean_cpu_forward_ms_per_question_all_candidates": mean(
                [r["model_cpu_forward_ms_all_candidates"] for r in selected]
            ),
            "mean_model_input_tokens_all_candidates": mean(
                [r["model_input_tokens_all_candidates"] for r in selected]
            ),
        }
    report = {
        "status": "PUBLIC_SQUAD_DEV_TASK_MATCHED_EXTRACTIVE_CONTROL_NOT_INDEPENDENT_VALIDATION",
        "model_role": "fine_tuned_extractive_qa_not_causal_generation",
        "data": benchmark.manifest(),
        "config": {
            "fixed_null_margin_threshold": 0.0,
            "top_k": 5,
            "tokenizer_max_len": 384,
            "max_answer_tokens": 25,
            "source_offset_verification": True,
            "reader_training_dataset": "SQuAD 2.0",
        },
        "by_mode": by_mode,
        "cases": rows,
        "limitations": [
            "Checkpoint was fine-tuned on SQuAD2: NOT fair architecture/model-size winner over non-finetuned causal LMs",
            "Public DEV has training/tuning overlap risk; no external heldout corroboration",
            "SQuAD impossible refers to original paragraph, not expanded candidate corpus",
            "Exact source quote is NOT semantic support or correct question answering",
            "Single tokenized window may truncate long original paragraphs",
            "Frozen null threshold 0 is not a calibrated uncertainty estimate",
            "Cross-passage logits may not be calibrated; top-5 increases multiple-comparison false positives",
            "No energy, independent annotation or multi-domain risk/coverage measurement",
        ],
    }
    return report, {"warmup_prediction": warmup[0].text, "warmup_ms": warmup[2]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--max-cases", type=int, default=32)
    parser.add_argument("--distractors", type=int, default=96)
    args = parser.parse_args()
    out = Path(args.output_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)
    path = out / "official_squad2_dev.json"
    download_public_dev(path)
    model_dir = out / "weights"
    model_info = download_reader(model_dir)
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    import torch

    torch.set_num_threads(2)
    started = time.perf_counter()
    result, diagnostic = evaluate(
        data_path=path, model_path=model_dir,
        max_cases=args.max_cases, distractors=args.distractors,
    )
    elapsed = time.perf_counter() - started
    score_path = out / "reference_qa_metrics.json"
    _write(score_path, result)
    manifest = {
        "status": result["status"],
        "model": model_info,
        "source_dataset_sha256": _file_hash(path),
        "metrics_sha256": _file_hash(score_path),
        "dataset_manifest": result["data"],
        "environment": {
            "python": platform.python_version(),
            "torch": torch.__version__,
            "github_sha": os.getenv("GITHUB_SHA"),
            "runner_os": os.getenv("RUNNER_OS"),
            "trial_wall_seconds": elapsed,
            "whole_process_peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        },
        "warmup": diagnostic,
        "limitations": result["limitations"],
    }
    _write(out / "integrity_manifest.json", manifest)
    print(json.dumps({
        "status": result["status"],
        "model_sha": model_info["revision"],
        "source_sha": manifest["source_dataset_sha256"],
        "by_mode": result["by_mode"],
    }))


if __name__ == "__main__":
    main()
