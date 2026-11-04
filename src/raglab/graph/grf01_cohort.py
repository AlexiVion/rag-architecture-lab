"""Freeze a disjoint future HotpotQA DEV cohort without benchmarking or tuning.

This is only a reproducible cohort reservation. It is NOT a truly independent
dataset because the source DEV split has already been explored by the project.
No models, answer generation, gold-score evaluation or parameter searches.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from raglab.graph.hotpotqa_benchmark import (
    DATASET_ID,
    HOTPOT_SHA256,
    cached_hotpotqa,
    load_bridge_dev_rows,
)

PREVIOUS_STUDY_ID = "GRF00-HOTPOTQA-DEV-01"
PREVIOUS_STUDY_SHA256 = (
    "962dc3b12d0086857ad94198cf2b1fff7a49ca5f7df069e9575a6daaf778f016"
)
COHORT_SCHEMA = "GRF01-RESERVED-DEV-01"
SELECTION_SEED = 217
COHORT_SIZE = 60


def _query_fingerprint(ids: list[str]) -> str:
    return hashlib.sha256("\n".join(ids).encode("utf-8")).hexdigest()


def select_disjoint_query_ids(
    candidate_ids: list[str],
    excluded_ids: set[str],
    *,
    count: int = COHORT_SIZE,
) -> list[str]:
    if type(count) is not int or count < 1:
        raise ValueError("Cohort size must be a positive integer")
    if len(set(candidate_ids)) != len(candidate_ids):
        raise ValueError("Duplicate eligible candidate IDs")
    if any(not isinstance(cid, str) or not cid for cid in candidate_ids):
        raise ValueError("Invalid eligible query ID")
    if any(not isinstance(cid, str) or not cid for cid in excluded_ids):
        raise ValueError("Invalid previously exposed query ID")
    fresh = [cid for cid in candidate_ids if cid not in excluded_ids]
    if len(fresh) < count:
        raise ValueError("Not enough disjoint eligible queries to reserve the cohort")
    selected = fresh[:count]
    if set(selected) & excluded_ids:
        raise AssertionError("The reserved query cohort overlaps the exposed study")
    return selected


def freeze_cohort(
    *,
    original_report_path: Path,
    dataset_cache: Path,
    output: Path,
) -> dict[str, Any]:
    raw = original_report_path.read_bytes()
    archive_sha = hashlib.sha256(raw).hexdigest()
    if archive_sha != PREVIOUS_STUDY_SHA256:
        raise ValueError(
            "Previous exposed GRF-00 report SHA256 is not the audited original"
        )
    old = json.loads(raw)
    if (
        old.get("experiment_id") != PREVIOUS_STUDY_ID
        or old.get("dataset") != DATASET_ID
        or old.get("dataset_sha256") != HOTPOT_SHA256
        or old.get("sample_seed") != 17
        or old.get("sample_count") != 60
    ):
        raise ValueError("Previous GRF-00 report provenance is inconsistent")
    cases = old.get("queries")
    if not isinstance(cases, list) or len(cases) != 60:
        raise ValueError("Previous GRF-00 case records missing")
    original_ids = [case.get("question_id") for case in cases]
    if (
        any(not isinstance(x, str) or not x for x in original_ids)
        or len(set(original_ids)) != len(original_ids)
        or _query_fingerprint(original_ids) != old.get("sample_query_ids_sha256")
    ):
        raise ValueError("Original GRF-00 exposed query IDs are inconsistent")

    source = cached_hotpotqa(dataset_cache)
    pool = load_bridge_dev_rows(source, seed=SELECTION_SEED, count=500)
    pool_ids = [case["_id"] for case in pool]
    selected = select_disjoint_query_ids(pool_ids, set(original_ids))
    manifest = {
        "schema_version": 1,
        "cohort_id": COHORT_SCHEMA,
        "status": "reserved_not_evaluated",
        "dataset": DATASET_ID,
        "dataset_sha256": HOTPOT_SHA256,
        "split": "dev/distractor",
        "question_type": "bridge",
        "eligibility": "at least two annotated support titles within candidate paragraphs",
        "eligibility_gold_usage": "used_only_to_select_eligible_questions",
        "selection_seed": SELECTION_SEED,
        "selection_pool_size": 500,
        "selection_rule": "SHA256(seed|original_query_id), then exclude all GRF00 audited query IDs",
        "reserved_query_ids": selected,
        "reserved_query_ids_sha256": _query_fingerprint(selected),
        "reserved_query_count": len(selected),
        "prior_exposed_run_sha256": archive_sha,
        "prior_exposed_query_ids_sha256": _query_fingerprint(original_ids),
        "overlap_count_with_grf00": 0,
        "evaluation_scores": None,
        "candidate_model_weights": None,
        "leakage_warning": (
            "Disjoint from the first 60 questions, but still drawn from the "
            "already explored DEV split. NOT an independent new dataset. "
            "Freeze architecture and model details before any evaluation."
        ),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
    if output.exists():
        if output.read_text(encoding="utf-8") != serialized:
            raise ValueError("Reserved cohort already exists and differs; refusing overwrite")
    else:
        with output.open("x", encoding="utf-8") as handle:
            handle.write(serialized)
    return manifest


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(
        description="Reserve a disjoint HotpotQA DEV cohort without model inference or tuning"
    )
    parser.add_argument(
        "--original-report",
        default="runs/graph-hotpotqa/GRF00_HOTPOTQA_20261104T163545630360Z.json",
    )
    parser.add_argument(
        "--dataset-cache",
        default=".cache/hotpotqa/hotpot_dev_distractor_v1.json",
    )
    parser.add_argument(
        "--output",
        default="runs/graph-hybrid/GRF01_RESERVED_DEV_COHORT.json",
    )
    args = parser.parse_args()
    path = Path(args.output)
    result = freeze_cohort(
        original_report_path=Path(args.original_report),
        dataset_cache=Path(args.dataset_cache),
        output=path,
    )
    print("GRF01_COHORT_RESERVATION_COMPLETE")
    print(f"GRF01_RESERVED_CASES={result['reserved_query_count']}")
    print(f"GRF01_PRIOR_OVERLAP={result['overlap_count_with_grf00']}")
    print(f"GRF01_QUERY_IDS_SHA256={result['reserved_query_ids_sha256']}")
    print(f"GRF01_MANIFEST={path}")
    print("No model, retrieval benchmark, qrel scoring or parameter tuning executed.")
    print("Disjoint DEV cohort is not an independent dataset.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
