"""Post-run audit of original Qwen M2 synthetic-control JSON; loads NO models."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from raglab.citations import validate_citations
from raglab.evaluation.m2_live_smoke import (
    DOCUMENTS, EXPERIMENT_ID, MODEL_ID, SCENARIOS, fixture_sha256,
)

ORIGINAL_FIXTURE_SHA256 = "261e4545b00e19d100e4144ca2704f7bac11658db1f200ef2601e58621e7e46c"


def citation_failure_reason(text: str, labels: list[str]) -> str:
    if not text.strip():
        return "empty_generation"
    report = validate_citations(text, labels)
    if report.citation_count == 0:
        return "no_bracketed_source_citations"
    if report.invalid_labels:
        return "unknown_source_citation_labels"
    if report.cited_sentence_count < report.sentence_count:
        return "not_all_sentences_cited"
    return "citation_syntax_passed" if report.citation_contract_passed else "other_syntax_failure"


def audit_saved_m2(
    artifact: dict[str, Any], input_sha256: str, *, require_real_model: bool = True
) -> dict[str, Any]:
    if (
        artifact.get("schema_version") != 1
        or artifact.get("experiment_id") != EXPERIMENT_ID
        or artifact.get("status") != "operational_synthetic_controls_not_semantic_quality_benchmark"
        or artifact.get("fixture_sha256") != fixture_sha256()
        or artifact.get("fixture_sha256") != ORIGINAL_FIXTURE_SHA256
        or artifact.get("case_count") != 4
        or artifact.get("total_generator_calls") != 3
        or artifact.get("source_selection") != "fixed_original_source_ids_not_retriever_evaluation"
        or artifact.get("generation_policy") != "model_greedy_decode_do_sample_false"
        or (require_real_model and artifact.get("model_id") != MODEL_ID)
    ):
        raise ValueError("Archived M2 experiment/fixture provenance mismatch")
    rows = artifact.get("cases")
    if not isinstance(rows, list) or len(rows) != len(SCENARIOS):
        raise ValueError("Missing original experiment cases")
    if [r.get("case_id") for r in rows] != [s["case_id"] for s in SCENARIOS]:
        raise ValueError("Changed control order or identifiers")
    documents = {d.id: d for d in DOCUMENTS}
    verified = []
    for row, spec in zip(rows, SCENARIOS, strict=True):
        result = row.get("local_answer_artifact")
        if not isinstance(result, dict):
            raise ValueError("Original serialized answer is missing")
        sources = result.get("sources")
        if not isinstance(sources, list) or len(sources) != len(spec["source_ids"]):
            raise ValueError("Wrong number of original source passages")
        labels = [f"S{i}" for i in range(1, len(sources) + 1)]
        for i, src in enumerate(sources):
            expected_doc = documents[spec["source_ids"][i]]
            if not isinstance(src, dict) or (
                src.get("label") != labels[i]
                or src.get("doc_id") != expected_doc.id
                or src.get("text") != expected_doc.text
                or src.get("title") != expected_doc.title
                or src.get("rank") != i + 1
            ):
                raise ValueError("Original source passage, ID or citation label was changed")
        calls = row.get("generator_calls")
        if type(calls) is not int or calls != int(bool(sources)):
            raise ValueError("Unexpected model-inference call count")
        status = result.get("output_status")
        if (
            row.get("output_status") != status
            or result.get("question") != spec["question"]
            or row.get("evidence_condition_curated_not_model_inferred") != spec["evidence_condition"]
            or row.get("expected_behavior_fictional_control") != spec["expected_behavior"]
            or row.get("semantic_support") != "not_evaluated"
            or row.get("task_correctness") != "not_evaluated"
            or row.get("expected_behavior_alignment") != "not_evaluated_requires_independent_review"
        ):
            raise ValueError("Control metadata or quality boundaries were changed")
        timings = result.get("timings_ms")
        if not isinstance(timings, dict):
            raise ValueError("Saved timing fields missing")
        for key in ("retrieval", "context", "generation", "total"):
            value = timings.get(key)
            if type(value) not in (float, int) or not math.isfinite(value) or value < 0:
                raise ValueError("Invalid recorded timing: " + key)
        if not sources:
            if (
                status != "abstained_no_context"
                or result.get("abstained") is not True
                or result.get("raw_generation") is not None
                or timings["generation"] != 0
                or calls != 0
            ):
                raise ValueError("No-context must abstain without invoking generator")
            original = result.get("answer")
        elif status == "rejected_citation_contract":
            if result.get("abstained") is not True:
                raise ValueError("Rejected draft must be marked abstained")
            original = result.get("raw_generation")
            if result.get("answer") != (
                "The generated draft failed the citation requirements; "
                "no factual answer is being provided."
            ):
                raise ValueError("Rejected draft leaked unapproved public text")
        elif status == "accepted":
            if result.get("abstained") is not False or result.get("raw_generation") is not None:
                raise ValueError("Accepted output must contain only public answer")
            original = result.get("answer")
        else:
            raise ValueError("Unexpected output state")
        if not isinstance(original, str):
            raise ValueError("Recorded original candidate text missing")
        recalculated = validate_citations(original, labels)
        saved = result.get("citation_report")
        # In-process RAGAnswer.to_dict() retains tuples from asdict(), while
        # the immutable archived JSON represents the exact same tuple fields
        # as arrays. Both shapes must match every value and expected field;
        # this is structural compatibility, NOT a weaker citation check.
        expected_report = asdict(recalculated)
        if not isinstance(saved, dict) or set(saved) != set(expected_report):
            raise ValueError("Recorded citation statistics disagree with original draft")
        for key, expected_value in expected_report.items():
            actual = saved[key]
            if isinstance(expected_value, tuple):
                if type(actual) not in (tuple, list) or tuple(actual) != expected_value:
                    raise ValueError("Recorded citation statistics disagree with original draft")
            elif type(actual) is not type(expected_value) or actual != expected_value:
                raise ValueError("Recorded citation statistics disagree with original draft")
        if row.get("citation_contract_syntax_passed") is not recalculated.citation_contract_passed:
            raise ValueError("Recorded citation-validity flag disagrees")
        if sources and ((status == "accepted") is not recalculated.citation_contract_passed):
            raise ValueError("Publication gate failed the original citation contract")
        if row.get("safe_publication_gate_passed") is not True:
            raise ValueError("Unsafe publication flag recorded")
        verified.append({
            "case_id": spec["case_id"],
            "output_status": status,
            "available_labels": labels,
            "source_document_ids": spec["source_ids"],
            "generator_calls": calls,
            "generation_ms": timings["generation"],
            "citation_count": recalculated.citation_count,
            "valid_citation_count": recalculated.valid_citation_count,
            "invalid_labels": list(recalculated.invalid_labels),
            "sentence_count": recalculated.sentence_count,
            "cited_sentence_count": recalculated.cited_sentence_count,
            "sentence_coverage": recalculated.sentence_coverage,
            "diagnostic": "not_applicable_no_context" if not sources
                else citation_failure_reason(original, labels),
            "original_draft_sha256": hashlib.sha256(original.encode("utf-8")).hexdigest()
                if sources else None,
            "original_draft_length": len(original) if sources else 0,
            "semantic_support": "NOT_EVALUATED",
            "task_correctness": "NOT_EVALUATED",
            "appropriateness_of_abstention": "NOT_EVALUATED",
        })
    if sum(row["generator_calls"] for row in verified) != 3:
        raise ValueError("Generator calls do not reconcile")
    if artifact.get("status_counts") != dict(Counter(x["output_status"] for x in rows)):
        raise ValueError("Saved output-status counts do not reconcile")
    if not isinstance(input_sha256, str) or len(input_sha256) != 64:
        raise ValueError("Original source hash invalid")
    return {
        "schema_version": 1,
        "experiment_id": EXPERIMENT_ID,
        "audit_status": "PASS_NO_NEW_MODEL_RUN",
        "source_report_sha256": input_sha256,
        "fixture_sha256": ORIGINAL_FIXTURE_SHA256,
        "model_id": artifact["model_id"],
        "model_commit_if_available": artifact.get("resolved_model_commit_if_available"),
        "case_count": len(verified),
        "cases": verified,
        "status_counts": artifact["status_counts"],
        "total_generator_calls": 3,
        "semantic_claims": "NOT_EVALUATED",
        "warning": "Citation syntax, source provenance and refusal status are not factuality.",
    }


def markdown_summary(report: dict[str, Any]) -> str:
    lines = [
        "# M2-LIVE-01 saved result audit (no model)",
        "",
        "Original SHA256: " + report["source_report_sha256"],
        "",
        "| Case | Output status | Syntax finding | Citation count | Coverage |",
        "|---|---|---|---:|---:|",
    ]
    for row in report["cases"]:
        lines.append(
            f"| {row['case_id']} | {row['output_status']} | {row['diagnostic']} | "
            f"{row['citation_count']} | {row['sentence_coverage']:.2f} |"
        )
    lines += ["", "Semantic support: NOT_EVALUATED.", ""]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit an archived M2 run, without inference")
    parser.add_argument("--input", default="runs/m2-live/M2_LIVE_20261104T182515461187Z.json")
    parser.add_argument("--output-dir", default="runs/m2-live")
    args = parser.parse_args()
    raw = Path(args.input).read_bytes()
    original = json.loads(raw)
    result = audit_saved_m2(original, hashlib.sha256(raw).hexdigest())
    folder = Path(args.output_dir)
    folder.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    json_out = folder / f"M2_LIVE_AUDIT_{stamp}.json"
    md_out = folder / f"M2_LIVE_AUDIT_{stamp}.md"
    with json_out.open("x", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    with md_out.open("x", encoding="utf-8") as handle:
        handle.write(markdown_summary(result))
    print("M2_SAVED_RUN_AUDIT_PASS")
    print("M2_ORIGINAL_REPORT_SHA256=" + result["source_report_sha256"])
    by_id = {c["case_id"]: c for c in original["cases"]}
    for row in result["cases"]:
        print("=== " + row["case_id"] + " ===")
        print("STATUS=" + row["output_status"])
        print("CAUSE=" + row["diagnostic"])
        print("AVAILABLE_LABELS=" + ",".join(row["available_labels"]))
        print(f"CITATIONS={row['citation_count']} VALID={row['valid_citation_count']} "
              f"SENTENCES={row['sentence_count']} CITED={row['cited_sentence_count']}")
        if row["generator_calls"]:
            draft = by_id[row["case_id"]]["local_answer_artifact"]["raw_generation"]
            if draft is None:
                draft = by_id[row["case_id"]]["local_answer_artifact"]["answer"]
            print("RAW_DRAFT_JSON=" + json.dumps(draft[:1800], ensure_ascii=False))
            if len(draft) > 1800:
                print("RAW_DRAFT_CONSOLE_TRUNCATED=true")
        else:
            print("GENERATOR_SKIPPED=true")
    print("M2_LOCAL_AUDIT_JSON=" + str(json_out))
    print("M2_LOCAL_AUDIT_MARKDOWN=" + str(md_out))
    print("SEMANTIC_SUPPORT=NOT_EVALUATED; NO_NEW_MODEL_RUN=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
