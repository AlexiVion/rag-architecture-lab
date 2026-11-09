"""Independent post-run inventory of M2-SYNTH-01 saved Qwen outputs.

This is a forensic audit of ORIGINAL files. No generation, reranking,
re-scoring with learned models, changes to defaults, or publication.
A syntactic 'accepted' pipeline status is not factual support.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from raglab.citations import validate_citations
from raglab.evaluation.m2_synth_protocol import (
    ABSTAIN, CATEGORIES, EXPECTED_CASES_SHA256, MODEL_ID, PROMPT_SHA256,
    aggregate_controls, canonical_sha256, score_observation, validate_protocol,
)
from raglab.evaluation.m2_synth_runner import (
    build_final_report, manifest_payload, verify_record, write_or_check,
)

NEGATIVES = {"irrelevant", "conflicting"}


def _read_json(path: Path) -> tuple[dict[str, Any], str]:
    blob = path.read_bytes()
    data = json.loads(blob)
    if not isinstance(data, dict):
        raise ValueError("Expected a JSON object at " + str(path))
    return data, hashlib.sha256(blob).hexdigest()


def audit_saved_study(folder: Path) -> dict[str, Any]:
    """Check the exact original 24 rows, reconstruct statistics and flag risk."""
    cases = validate_protocol()
    manifest, manifest_sha = _read_json(folder / "manifest.json")
    if manifest != manifest_payload():
        raise ValueError("Frozen manifest differs from preregistered protocol")
    source_report, report_sha = _read_json(folder / "report.json")
    paths = [folder / "cases" / f"{i:02d}.json" for i in range(1, 25)]
    existing = sorted((folder / "cases").glob("*.json"))
    if sorted(paths) != existing:
        raise ValueError("Missing, extra or renamed case files in 24-case archive")
    records: list[dict[str, Any]] = []
    file_hashes: list[str] = []
    for case, path in zip(cases, paths, strict=True):
        record, file_sha = _read_json(path)
        # Validate saved raw source text, question, model-generated output,
        # original publication status and both citation parsers.
        verify_record(case, record)
        src_artifact = record["original_answer_artifact"]
        if src_artifact.get("generator_name") != record.get("observed_generator_name"):
            raise ValueError("Archived generator identity differs")
        saved_report = src_artifact.get("citation_report")
        if not isinstance(saved_report, dict):
            raise ValueError("Original citation report is missing")
        draft = record["raw_candidate"]
        labels = [f"S{i}" for i in range(1, len(case["sources"]) + 1)]
        from dataclasses import asdict
        v1 = validate_citations(draft if draft is not None else src_artifact["answer"], labels)
        if saved_report != json.loads(json.dumps(asdict(v1))):
            raise ValueError("Original citation report differs from raw model answer")
        if record.get("model_calls") != int(bool(case["sources"])):
            raise ValueError("Saved generator calls differ from source condition")
        if any(
            name not in src_artifact.get("timings_ms", {})
            for name in ("retrieval", "context", "generation", "total")
        ):
            raise ValueError("Missing original timings")
        if case["category"] == "no_context":
            if src_artifact["timings_ms"]["generation"] != 0 or draft is not None:
                raise ValueError("No-context case did not skip model generation")
        records.append(record)
        file_hashes.append(file_sha)

    reconstructed = build_final_report(cases, records)
    if source_report != reconstructed:
        raise ValueError("Original aggregate report differs from saved case data")
    if reconstructed.get("source_cases_sha256") != EXPECTED_CASES_SHA256:
        raise ValueError("Cohort fingerprint changed")
    if reconstructed.get("prompt_sha256") != PROMPT_SHA256:
        raise ValueError("Prompt fingerprint changed")
    if reconstructed.get("model_id") != MODEL_ID:
        raise ValueError("Unexpected local model identity")
    if reconstructed.get("model_calls") != 18:
        raise ValueError("Unexpected model call count")
    if reconstructed.get("publication_actions") != 0:
        raise ValueError("External publication claimed by archived study")

    details: list[dict[str, Any]] = []
    for case, record, case_sha in zip(cases, records, file_hashes, strict=True):
        raw = record["raw_candidate"]
        scored = score_observation(case, record)
        category = case["category"]
        expected_abstention = category in NEGATIVES
        accepted = record["pipeline_status"] == "accepted"
        details.append({
            "case_id": case["case_id"],
            "category": category,
            "case_file_sha256": case_sha,
            "source_ids": record["source_ids"],
            "source_count": len(case["sources"]),
            "raw_candidate": raw,
            "raw_candidate_sha256": hashlib.sha256(raw.encode("utf-8")).hexdigest()
                if raw is not None else None,
            "model_calls_original": record["model_calls"],
            "historical_pipeline_status": record["pipeline_status"],
            "citation_v1_syntax": record["syntax_v1_pass"],
            "citation_v2_syntax_only": record["syntax_v2_pass"],
            "exact_model_abstention": raw.strip() == ABSTAIN if isinstance(raw, str) else False,
            "known_answer_literal_present": scored["literal_match_diagnostic"],
            "synthetic_control_success": scored["control_success"],
            "pipeline_accepted_when_curated_abstention_expected": expected_abstention and accepted,
            "raw_factual_attempt_when_curated_abstention_expected": (
                expected_abstention and isinstance(raw, str) and raw.strip() != ABSTAIN
            ),
            "semantic_entailment": "NOT_EVALUATED",
            "task_alignment": "NOT_EVALUATED",
            "publication_to_external_system": False,
        })
    accepted_negatives = [row for row in details
                          if row["pipeline_accepted_when_curated_abstention_expected"]]
    expected_abstentions = [row for row in details if row["category"] in NEGATIVES]
    if len(expected_abstentions) != 12:
        raise ValueError("Incorrect negative-control denominator")
    accepted_nonempty = sum(row["historical_pipeline_status"] == "accepted"
                            for row in details if row["model_calls_original"] == 1)

    return {
        "schema_version": 1,
        "study_id": "M2-SYNTH-01-ARCHIVED-OUTPUT-FORENSIC-AUDIT",
        "audit_status": "ARCHIVED_FILES_RECONCILED_NO_MODEL_EXECUTION",
        "report_original_sha256": report_sha,
        "manifest_original_sha256": manifest_sha,
        "case_set_sha256": EXPECTED_CASES_SHA256,
        "unchanged_prompt_sha256": PROMPT_SHA256,
        "model_id": MODEL_ID,
        "model_revision_if_resolved": reconstructed["model_revision_if_resolved"],
        "original_model_calls": reconstructed["model_calls"],
        "new_model_calls": 0,
        "external_publications": 0,
        "total_cases": 24,
        "total_control_success": sum(row["synthetic_control_success"] for row in details),
        "control_success_by_category": {
            category: {
                "cases": sum(row["category"] == category for row in details),
                "success": sum(row["synthetic_control_success"] for row in details if row["category"] == category),
                "original_pipeline_accepted": sum(row["historical_pipeline_status"] == "accepted"
                    for row in details if row["category"] == category),
                "experimental_citation_v2_pass": sum(row["citation_v2_syntax_only"]
                    for row in details if row["category"] == category),
                "exact_model_abstention": sum(row["exact_model_abstention"]
                    for row in details if row["category"] == category),
            } for category in CATEGORIES
        },
        "negative_control_pipeline_acceptance_count": len(accepted_negatives),
        "negative_control_denominator": 12,
        "negative_control_pipeline_acceptance_rate": len(accepted_negatives) / 12,
        "original_pipeline_accepted_nonempty_count": accepted_nonempty,
        "safety_interpretation": (
            "Pipeline syntactic acceptance of a response to a curated insufficient/"
            "contradictory-evidence condition is a development risk signal, "
            "not independently verified factual incorrectness. No responses were published."
        ),
        "research_decision": "NO_GO_AUTOMATIC_ANSWER_PUBLICATION_UNTIL_SOURCE_SUPPORT_GATE_VALIDATED",
        "cases": details,
        "limitations": [
            "Original 24-case set is six templated fictional groups, not a natural held-out QA dataset.",
            "Answerable success requires literal manufacturer+syntax, not independently judged entailment.",
            "Negative-case expected abstentions are by authored construction, not human expert annotation.",
            "The unchanged RAG pipeline accepts syntax-only citations and is not a support verifier.",
            "The 24 Qwen generations/no-context skips are archived; this audit called no model.",
            "Neither a different prompt nor a semantic verifier is tested here.",
            "Qwen model revision may be unresolved; do not claim fully pinned weights.",
        ],
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# M2-SYNTH-01 — original 24-case saved-result audit",
        "",
        f"Original report SHA256: \\`{report['report_original_sha256']}\\`",
        f"Original manifest SHA256: \\`{report['manifest_original_sha256']}\\`",
        f"Outcome: **{report['research_decision']}**",
        "",
        "| Control | n | Success | Pipeline accepted | V2 citation syntax | Model exact abstention |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for group, stats in report["control_success_by_category"].items():
        lines.append(
            f"| {group} | {stats['cases']} | {stats['success']} | "
            f"{stats['original_pipeline_accepted']} | "
            f"{stats['experimental_citation_v2_pass']} | "
            f"{stats['exact_model_abstention']} |"
        )
    lines += [
        "",
        f"Negative controls (irrelevant/conflicting) syntactically accepted by original pipeline: "
        f"**{report['negative_control_pipeline_acceptance_count']} / "
        f"{report['negative_control_denominator']}**.",
        "",
        "## Narrow scientific boundaries",
        "",
        *["- " + limitation for limitation in report["limitations"]],
        "",
        "All original candidate texts and full source passages stay in local gitignored files.",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit saved M2-SYNTH-01 rows, no Qwen")
    parser.add_argument("--run-dir", default="runs/m2-synth01")
    args = parser.parse_args()
    folder = Path(args.run_dir)
    report = audit_saved_study(folder)
    output_dir = folder / "audits"
    prefix = report["report_original_sha256"][:16]
    json_path = output_dir / ("M2_SYNTH01_AUDIT_" + prefix + ".json")
    md_path = output_dir / ("M2_SYNTH01_AUDIT_" + prefix + ".md")
    write_or_check(json_path, report)
    body = render_markdown(report)
    if md_path.exists():
        if md_path.read_text(encoding="utf-8") != body:
            raise FileExistsError("Existing Markdown audit differs; refusing overwrite")
    else:
        md_path.parent.mkdir(parents=True, exist_ok=True)
        with md_path.open("x", encoding="utf-8") as handle:
            handle.write(body)
    print("M2_SYNTH01_ARCHIVED_AUDIT_PASS")
    print("M2_ORIGINAL_REPORT_SHA256=" + report["report_original_sha256"])
    print("M2_ORIGINAL_MANIFEST_SHA256=" + report["manifest_original_sha256"])
    print("M2_RESEARCH_DECISION=" + report["research_decision"])
    print("M2_ALL_CONTROLS_PASSED=" + str(report["total_control_success"]) + "/24")
    print("M2_NEGATIVE_PIPELINE_ACCEPTANCE="
          + str(report["negative_control_pipeline_acceptance_count"]) + "/12")
    for group, stats in report["control_success_by_category"].items():
        print("M2_CATEGORY=" + group + " PASS=" + str(stats["success"]) + "/"
              + str(stats["cases"]) + " PIPELINE_ACCEPTED="
              + str(stats["original_pipeline_accepted"])
              + " SYNTAX_V2=" + str(stats["experimental_citation_v2_pass"])
              + " MODEL_ABSTAINED_EXACT=" + str(stats["exact_model_abstention"]))
    for row in report["cases"]:
        if row["model_calls_original"]:
            print(f"CASE={row['case_id']} CATEGORY={row['category']} "
                  f"STATUS={row['historical_pipeline_status']} "
                  f"V2_CITATION={row['citation_v2_syntax_only']} "
                  f"CONTROL_PASS={row['synthetic_control_success']}")
            print("RAW_QWEN_JSON="
                  + json.dumps(row["raw_candidate"][:1500], ensure_ascii=False))
    print("M2_AUDIT_LOCAL_JSON=" + str(json_path))
    print("M2_AUDIT_LOCAL_MARKDOWN=" + str(md_path))
    print("NO_MODEL_RERUN=true; SEMANTIC_ACCURACY=NOT_EVALUATED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
