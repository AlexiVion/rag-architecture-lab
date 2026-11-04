"""M2-LIVE-02 immutable output replay under proposed opt-in citation parser v2.

Reads one already-run Qwen output. NEVER calls a generator or mutates
RAGPipeline. A syntax-only counterfactual is not a semantic correctness score.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from dataclasses import asdict
from pathlib import Path
from typing import Any

from raglab.citations import validate_citations
from raglab.citations.validator_v2 import validate_citations_v2
from raglab.evaluation.m2_live_smoke import DOCUMENTS, MODEL_ID, SCENARIOS, fixture_sha256
from raglab.evaluation.m2_live_v2 import (
    EXPERIMENT_ID, ORIGINAL_REPORT_SHA256, PROMPT_VERSION, prompt_sha256,
)

ORIGINAL_EXPERIMENT_FILE = (
    "runs/m2-live-v2/M2_LIVE02_20261104T185026616108Z.json"
)
EXPECTED_DRAFTS = {
    "answerable_supplied_evidence": (
        "Meridian Robotics developed the Orion Navigation System "
        "used by the Aster Rover. [S1]"
    ),
    "irrelevant_nonempty_evidence": (
        "Helios Instruments developed the Orion Navigation System "
        "for the Aster Rover [Solis Probe]."
    ),
    "contradictory_evidence": "The Zenith Probe launched on July 9, 2021.",
}


def replay_saved_run(source: dict[str, Any], report_sha256: str) -> dict[str, Any]:
    """Compare old vs new *citation syntax* on exact frozen raw Qwen outputs."""
    if (
        source.get("schema_version") != 1
        or source.get("experiment_id") != EXPERIMENT_ID
        or source.get("prompt_version") != PROMPT_VERSION
        or source.get("prompt_sha256") != prompt_sha256()
        or source.get("fixture_sha256") != fixture_sha256()
        or source.get("baseline_report_sha256") != ORIGINAL_REPORT_SHA256
        or source.get("model_id") != MODEL_ID
        or source.get("generator_calls") != 3
        or source.get("case_count") != 4
        or source.get("max_new_tokens") != 128
        or source.get("decoding") != "greedy_do_sample_false"
        or source.get("publication_policy") != "ALL_OUTPUTS_RESEARCH_ONLY_HELD_FOR_SEMANTIC_REVIEW"
    ):
        raise ValueError("Archived M2-LIVE-02 protocol, model or fixture mismatch")
    rows = source.get("cases")
    if not isinstance(rows, list) or len(rows) != len(SCENARIOS):
        raise ValueError("Archived M2-LIVE-02 cases are missing")
    if [row.get("case_id") for row in rows] != [spec["case_id"] for spec in SCENARIOS]:
        raise ValueError("Archived case identities or order changed")
    documents = {d.id: d for d in DOCUMENTS}
    findings = []
    for row, spec in zip(rows, SCENARIOS, strict=True):
        case_id = spec["case_id"]
        if (
            row.get("original_source_ids") != spec["source_ids"]
            or row.get("curated_condition_not_model_inferred") != spec["evidence_condition"]
            or row.get("curated_expectation_not_a_score") != spec["expected_behavior"]
            or row.get("published_to_external_system") is not False
            or row.get("semantic_entailment") != "NOT_EVALUATED"
            or row.get("task_alignment") != "NOT_EVALUATED"
            or row.get("abstention_appropriateness") != "NOT_EVALUATED"
        ):
            raise ValueError("Source, quarantine or semantic boundaries changed")
        answer = row.get("local_answer_artifact")
        if not isinstance(answer, dict):
            raise ValueError("Missing original answer provenance")
        sources = answer.get("sources")
        if not isinstance(sources, list) or len(sources) != len(spec["source_ids"]):
            raise ValueError("Recorded source list differs from frozen fixture")
        for i, (src, doc_id) in enumerate(zip(sources, spec["source_ids"], strict=True), start=1):
            document = documents[doc_id]
            if not isinstance(src, dict) or any((
                src.get("label") != f"S{i}",
                src.get("doc_id") != doc_id,
                src.get("title") != document.title,
                src.get("text") != document.text,
                src.get("rank") != i,
            )):
                raise ValueError("Archived citation labels or source evidence changed")
        calls = row.get("model_calls")
        if type(calls) is not int or calls != int(bool(sources)):
            raise ValueError("Archived model call count changed")
        status = row.get("pipeline_output_status")
        if status != answer.get("output_status"):
            raise ValueError("Original pipeline publication status changed")
        candidate = row.get("generated_candidate_raw")
        if sources:
            if status != "rejected_citation_contract":
                raise ValueError("Unexpected new accepted status in archived original run")
            if candidate != EXPECTED_DRAFTS[case_id] or candidate != answer.get("raw_generation"):
                raise ValueError("Raw Qwen text differs from operator-audited original")
            if answer.get("answer") != (
                "The generated draft failed the citation requirements; "
                "no factual answer is being provided."
            ):
                raise ValueError("Rejected answer exposed unapproved text")
        else:
            if (
                status != "abstained_no_context" or calls != 0 or candidate is not None
                or answer.get("raw_generation") is not None
                or answer.get("timings_ms", {}).get("generation") != 0
            ):
                raise ValueError("No-context generator skip was changed")
        text = candidate if sources else answer.get("answer")
        if not isinstance(text, str):
            raise ValueError("Archived model/public text missing")
        legacy = validate_citations(text, [s["label"] for s in sources])
        v2 = validate_citations_v2(text, [s["label"] for s in sources])
        archived_report = answer.get("citation_report")
        if archived_report != json.loads(json.dumps(asdict(legacy))):
            raise ValueError("Archived citation report differs from original V1 parser")
        if row.get("citation_syntax_passed") is not legacy.citation_contract_passed:
            raise ValueError("Archived citation-contract verdict was modified")
        findings.append({
            "case_id": case_id,
            "archived_pipeline_status": status,
            "model_calls": calls,
            "citation_syntax_v1": legacy.citation_contract_passed,
            "citation_syntax_v2_counterfactual": v2.citation_contract_passed,
            "v2_sentence_count": v2.sentence_count,
            "v2_cited_sentence_count": v2.cited_sentence_count,
            "v2_invalid_citation_labels": list(v2.invalid_labels),
            "source_ids": list(spec["source_ids"]),
            "raw_candidate_sha256": (
                hashlib.sha256(candidate.encode("utf-8")).hexdigest()
                if candidate is not None else None
            ),
            "original_publication_status_unmodified": True,
            "semantically_supported": "NOT_EVALUATED",
            "answer_task_correctness": "NOT_EVALUATED",
            "appropriate_abstention": "NOT_EVALUATED",
        })
    if source.get("pipeline_status_counts") != dict(Counter(
        row["pipeline_output_status"] for row in rows
    )):
        raise ValueError("Archived status counts are inconsistent")
    return {
        "schema_version": 1,
        "experiment_id": "M2-LIVE-02-OFFLINE-CITATION-PARSER-REPLAY",
        "kind": "syntax_only_counterfactual_not_model_quality",
        "source_report_sha256": report_sha256,
        "source_prompt_sha256": source["prompt_sha256"],
        "source_fixture_sha256": source["fixture_sha256"],
        "source_baseline_sha256": source["baseline_report_sha256"],
        "archived_model_id": source["model_id"],
        "parser_candidate": "citation-v2-post-punctuation-strict",
        "model_calls_during_replay": 0,
        "publication_actions": 0,
        "v1_citation_pass_count": sum(r["citation_syntax_v1"] for r in findings),
        "v2_citation_pass_count": sum(r["citation_syntax_v2_counterfactual"] for r in findings),
        "cases": findings,
        "review_status": "RESEARCH_ONLY_NOT_APPROVED_FOR_PRODUCTION",
        "limitations": [
            "The existing pipeline is NOT changed or re-evaluated.",
            "Counterfactual parser syntax, not newly generated model output.",
            "One syntax-valid answer does NOT establish relevance, entailment or truth.",
            "The same four exposed fictional controls cannot provide held-out quality metrics.",
            "New parser may only be promoted after separate security, semantics and regression review.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Replay archived M2 citation syntax without rerunning Qwen"
    )
    parser.add_argument("--original", default=ORIGINAL_EXPERIMENT_FILE)
    parser.add_argument("--output", default="runs/m2-parser-replay/M2_LIVE02_SYNTAX_REPLAY.json")
    opts = parser.parse_args()
    raw = Path(opts.original).read_bytes()
    summary = replay_saved_run(json.loads(raw), hashlib.sha256(raw).hexdigest())
    output = Path(opts.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as file:
        json.dump(summary, file, ensure_ascii=False, indent=2)
        file.write("\n")
    print("M2_V2_ARCHIVED_SYNTAX_REPLAY_COMPLETE")
    print("M2_ARCHIVED_MODEL_SHA256=" + summary["source_report_sha256"])
    print("M2_PARSER_V1_CITATION_PASS_COUNT=" + str(summary["v1_citation_pass_count"]))
    print("M2_PARSER_V2_CITATION_PASS_COUNT=" + str(summary["v2_citation_pass_count"]))
    for row in summary["cases"]:
        print(f"M2_CASE={row['case_id']} STATUS={row['archived_pipeline_status']} "
              f"V1_SYNTAX={row['citation_syntax_v1']} "
              f"V2_SYNTAX_ONLY={row['citation_syntax_v2_counterfactual']} "
              f"V2_INVALID_LABELS={row['v2_invalid_citation_labels']}")
    print("M2_REPLAY_SAVED=" + str(output))
    print("SEMANTIC_SUPPORT=NOT_EVALUATED; MODEL_CALLS=0; PUBLICATION_ACTIONS=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
