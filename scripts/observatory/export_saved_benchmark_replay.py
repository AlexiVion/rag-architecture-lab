"""Convert one saved raglab benchmark bundle to a small first-N query replay.

No models, benchmarks or dataset downloads run. The input must be a single
original JSON bundle from raglab benchmark, not aggregate Markdown numbers.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path


def fail(message: str):
    raise ValueError("Invalid saved benchmark archive: " + message)


def export_saved_benchmark(raw: dict, *, source_sha256: str, take: int = 3) -> dict:
    if not isinstance(raw, dict) or not isinstance(raw.get("dataset"), str):
        fail("dataset absent")
    if not 1 <= take <= 20:
        fail("take must be between 1 and 20")
    pipelines = raw.get("pipelines")
    results = raw.get("results")
    if not isinstance(pipelines, list) or not isinstance(results, list):
        fail("pipeline list missing")
    if not 2 <= len(pipelines) <= 4 or len(pipelines) != len(results) or len(set(pipelines)) != len(pipelines):
        fail("require 2 to 4 distinct pipelines from the SAME saved run bundle")
    if not all(p in ("bm25", "dense", "hybrid", "hybrid-rerank", "bm25-rerank", "dense-rerank") for p in pipelines):
        fail("unsupported pipeline")
    if not isinstance(source_sha256, str) or len(source_sha256) != 64:
        fail("missing archive sha256")
    expected_ids = None
    environment = None
    document_count = None
    ordered = []
    for name, result in zip(pipelines, results, strict=True):
        if not isinstance(result, dict) or result.get("pipeline") != name or result.get("dataset") != raw["dataset"]:
            fail("pipeline/dataset mismatch")
        if not isinstance(result.get("queries"), list) or not result["queries"]:
            fail("missing original per-query records")
        if result.get("query_count") != len(result["queries"]):
            fail("query count differs")
        if not isinstance(result.get("environment"), dict):
            fail("no run environment")
        if environment is None:
            environment = result["environment"]
            document_count = result.get("document_count")
            if not isinstance(document_count, int) or document_count <= 0:
                fail("document count absent")
        elif result["environment"] != environment or result.get("document_count") != document_count:
            fail("pipelines were not recorded on same environment/corpus count")
        current_ids = [(q.get("query_id"), q.get("query")) for q in result["queries"]]
        if not all(isinstance(k, str) and k and isinstance(text, str) and text for k, text in current_ids):
            fail("missing query IDs or query text")
        if len(set(k for k, _ in current_ids)) != len(current_ids):
            fail("duplicate query IDs")
        if expected_ids is None:
            expected_ids = current_ids
        elif current_ids != expected_ids:
            fail("queries mismatch; unrelated runs cannot be merged")
        ordered.append(result["queries"])
    assert expected_ids is not None
    rows = []
    for idx in range(min(take, len(expected_ids))):
        id_, question = expected_ids[idx]
        rank_by_pipeline = {}
        for name, run in zip(pipelines, ordered, strict=True):
            candidates = run[idx].get("results")
            if not isinstance(candidates, list) or not candidates:
                fail("missing original ranked candidates")
            seen = set()
            list_rows = []
            for j, candidate in enumerate(candidates[:10], start=1):
                if not isinstance(candidate, dict):
                    fail("invalid ranked candidate")
                docid = candidate.get("doc_id")
                score = candidate.get("score")
                if not isinstance(docid, str) or not docid or docid in seen:
                    fail("duplicate/blank result document ID")
                if candidate.get("rank") != j or not isinstance(score, (float, int)) or not math.isfinite(score):
                    fail("invalid original rank or score")
                seen.add(docid)
                list_rows.append({"doc_id": docid, "rank": j, "score": score})
            rank_by_pipeline[name] = list_rows
        rows.append({"id": id_, "text": question, "rankings": rank_by_pipeline})
    return {
        "schema_version": 1,
        "kind": "saved_benchmark_query_replay",
        "status": "archived_original_per_query_not_independently_revalidated",
        "dataset": raw["dataset"],
        "source_archive_sha256": source_sha256,
        "document_count": document_count,
        "pipeline_names": pipelines,
        "query_selection": "first_N_original_order_without_qrel_selection",
        "source_environment": environment,
        "queries": rows,
        "limitations": [
            "Replayed from an existing single saved benchmark bundle, not a newly executed run.",
            "Archive hash authenticates the input bytes, not external dataset or model revisions.",
            "No independent label validation or semantic answer-correctness assessment.",
            "Only the original top ten retrieved results are exposed; absent IDs are out-of-depth.",
            "Do not compare this archive's latency directly with a different machine or run.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Original raglab benchmark JSON bundle")
    parser.add_argument("--output", default="benchmarks/results/local-query-replay.json")
    parser.add_argument("--take", type=int, default=3)
    args = parser.parse_args()
    source = Path(args.input).read_bytes()
    archive = json.loads(source.decode("utf-8"))
    payload = export_saved_benchmark(
        archive, source_sha256=hashlib.sha256(source).hexdigest(), take=args.take,
    )
    out = Path(args.output)
    if out.resolve() == Path(args.input).resolve():
        fail("output must not overwrite the input archive")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("SAVED_BENCHMARK_REPLAY=EXPORTED_NO_MODEL_CALLS")
    print("DATASET=" + payload["dataset"])
    print("SOURCE_SHA256=" + payload["source_archive_sha256"])
    print("OUTPUT=" + str(out))


if __name__ == "__main__":
    main()
