"""M2-GUARD-DEV-01: counterfactual rule-based gate on archived 24 cases.

No Qwen inference, no changed source, no new held-out score, no publication.
Prototypes a *narrow* English equipment-relationship parser as development
only. This replay's cohort has already been seen and is not validation.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from raglab.evaluation.m2_guard_dev01 import assess_candidate, assess_evidence
from raglab.evaluation.m2_synth01_audit import audit_saved_study
from raglab.evaluation.m2_synth_protocol import validate_protocol
from raglab.evaluation.m2_synth_runner import write_or_check

SOURCE_REPORT_SHA256 = "f33eade629967ff9c4c15bf3ce3e05ca4adc329ece837017bd0fd9ce6ef109e4"
SOURCE_MANIFEST_SHA256 = "c5a528a2f7c77c66ba0b56b151fc9909cbcddac5fad491d8f59cf4af8e4efa74"
EXPERIMENT_ID = "M2-GUARD-DEV-01-EXPOSED-SYNTHETIC-REPLAY"


def replay_archived_guard(folder: Path, *, check_pinned_original: bool = True) -> dict[str, Any]:
    audit = audit_saved_study(folder)
    if check_pinned_original and (
        audit["report_original_sha256"] != SOURCE_REPORT_SHA256
        or audit["manifest_original_sha256"] != SOURCE_MANIFEST_SHA256
    ):
        raise ValueError("Archived original report/manifest does not match operator-verified SHA256")
    cases = validate_protocol()
    if len(audit["cases"]) != 24 or len(cases) != 24:
        raise ValueError("Expected 24 original archived cases")
    rows = []
    for case, saved in zip(cases, audit["cases"], strict=True):
        if saved["case_id"] != case["case_id"]:
            raise ValueError("Archived case order differs from frozen cohort")
        decision = assess_evidence(case["question"], case["sources"])
        after = assess_candidate(case["question"], case["sources"], saved["raw_candidate"])
        if after["safe_to_publish"] is not False:
            raise ValueError("Research-only candidate unexpectedly publishable")
        rows.append({
            "case_id": case["case_id"],
            # Categories are retained only for *retrospective* diagnostics;
            # the rule engine takes only question and source texts.
            "author_category_for_diagnostic_only": case["category"],
            "archived_pipeline_status": saved["historical_pipeline_status"],
            "archived_raw_candidate_sha256": saved["raw_candidate_sha256"],
            "before_generation": decision.as_dict(),
            "strict_development_output_match": after["development_match"],
            "postgeneration_reason": after["reason"],
            "potential_model_calls_skipped_if_pre_gate_had_existed": (
                int(bool(case["sources"]) and not decision.allow_generation)
            ),
            "counterfactual_guard_would_have_blocked_archived_accepted_negative": (
                case["category"] in ("irrelevant", "conflicting")
                and saved["historical_pipeline_status"] == "accepted"
                and not decision.allow_generation
            ),
            "external_publication": False,
            "semantic_truth": "NOT_EVALUATED",
        })
    allow = [row for row in rows if row["before_generation"]["allow_generation"]]
    denial = [row for row in rows if not row["before_generation"]["allow_generation"]]
    accepted_risks = [
        row for row in rows
        if row["counterfactual_guard_would_have_blocked_archived_accepted_negative"]
    ]
    return {
        "schema_version": 1,
        "experiment_id": EXPERIMENT_ID,
        "status": "POST_HOC_EXPOSED_DEVELOPMENT_ONLY_NOT_HELD_OUT",
        "source_original_report_sha256": audit["report_original_sha256"],
        "source_original_manifest_sha256": audit["manifest_original_sha256"],
        "source_cases_sha256": audit["case_set_sha256"],
        "model_calls_during_replay": 0,
        "publication_actions": 0,
        "original_model_calls": 18,
        "hypothetical_pregen_allow_count": len(allow),
        "hypothetical_pregen_deny_count": len(denial),
        "hypothetical_model_calls_skipped_if_guard_existed": sum(
            row["potential_model_calls_skipped_if_pre_gate_had_existed"] for row in rows
        ),
        "original_syntax_accepted_negative_count": audit["negative_control_pipeline_acceptance_count"],
        "hypothetically_blocked_original_negative_acceptances": len(accepted_risks),
        "strict_template_post_match_with_original_drafts": sum(
            row["strict_development_output_match"] for row in rows
        ),
        "guard_denial_reasons": dict(Counter(row["before_generation"]["reason"] for row in denial)),
        "per_case": rows,
        "scientific_limits": [
            "Model outputs were observed BEFORE this guard was designed; this is post-hoc.",
            "A narrow exact-pattern English manufacturer parser is not natural-language entailment.",
            "The original 24 cases cannot become a fresh independent validation set.",
            "Hypothetical model-call avoidance is simulated; Qwen was not actually reinvoked.",
            "No factual statement is approved for publication even if template match succeeds.",
            "The existing RAGPipeline and its default evidence_gate=None are unchanged.",
        ],
        "research_recommendation": "KEEP_GUARD_DEV_ONLY_REQUIRE_NEW_DISJOINT_PREDECLARED_CASES",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Replay narrow M2 guard without inference")
    parser.add_argument("--source-dir", default="runs/m2-synth01")
    parser.add_argument("--output", default="runs/m2-guard-dev01/counterfactual.json")
    opts = parser.parse_args()
    report = replay_archived_guard(Path(opts.source_dir))
    created = write_or_check(Path(opts.output), report)
    print("M2_GUARD_DEV01_OFFLINE_REPLAY_PASS")
    print("M2_SOURCE_REPORT_SHA256=" + report["source_original_report_sha256"])
    print("M2_SOURCE_MANIFEST_SHA256=" + report["source_original_manifest_sha256"])
    print("M2_EVIDENCE_GATE_HYPOTHETICAL_ALLOW=" + str(report["hypothetical_pregen_allow_count"]))
    print("M2_EVIDENCE_GATE_HYPOTHETICAL_DENY=" + str(report["hypothetical_pregen_deny_count"]))
    print("M2_NEGATIVE_ORIGINAL_ACCEPTANCES_BLOCKED_HYPOTHETICAL="
          + str(report["hypothetically_blocked_original_negative_acceptances"]))
    print("M2_STRICT_POSTGEN_DEVELOPMENT_MATCHES="
          + str(report["strict_template_post_match_with_original_drafts"]))
    for reason, count in sorted(report["guard_denial_reasons"].items()):
        print("M2_GUARD_DENIAL=" + reason + " COUNT=" + str(count))
    print("M2_OUTPUT_STATE=" + ("CREATED" if created else "ALREADY_IDENTICAL"))
    print("M2_OUTPUT_LOCAL_JSON=" + opts.output)
    print("MODEL_CALLS=0; EXTERNAL_PUBLICATIONS=0; HELD_OUT_SCORE=NONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
