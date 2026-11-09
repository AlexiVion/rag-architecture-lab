"""M2-REVIEW-02: export UNLABELLED semantic review packets from archived Qwen.

No generation, model loading, qrels, benchmark reuse, auto-labelling, or
changes to legacy pipeline. The original parser is never promoted.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from raglab.citations.validator_v2 import _sentence_parts, validate_citations_v2
from raglab.evaluation.m2_live_v2_replay import (
    ORIGINAL_EXPERIMENT_FILE, replay_saved_run,
)
from raglab.evaluation.semantic_review import (
    prepare_review_packet, summarize_review_packet,
)

EXPECTED_REPORT_SHA256 = "3c9fc0794ab2d2bd3ca10825585926083b0d40067c1696aa77fc90f230ea7816"
STUDY_ID = "M2-REVIEW-02-EXPOSED-FICTIONAL"
_CITATION = re.compile(r"\[(S[1-9]\d*)\]")
_BRACKET = re.compile(r"\[[^\[\]\r\n]{1,80}\]")


def _review_claims(original: str) -> list[dict[str, Any]]:
    """Preserve post-punctuation citations with the previous claim."""
    claims = []
    for fragment in _sentence_parts(original):
        without_citations = _BRACKET.sub("", fragment).strip()
        if not any(char.isalpha() for char in without_citations):
            continue
        claims.append({
            "claim_id": len(claims) + 1,
            "text": fragment,
            "citation_labels": list(dict.fromkeys(_CITATION.findall(fragment))),
            "support": "unreviewed",
            "reviewed_evidence_labels": [],
            "notes": "",
        })
    return claims


def make_review_packets(
    archived: dict[str, Any], raw_sha256: str
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if raw_sha256 != EXPECTED_REPORT_SHA256:
        raise ValueError("Original M2-LIVE-02 report SHA256 does not match verified archive")
    replay = replay_saved_run(archived, raw_sha256)
    if (replay["model_calls_during_replay"] != 0 or replay["publication_actions"] != 0
        or replay["v1_citation_pass_count"] != 0
        or replay["v2_citation_pass_count"] != 1):
        raise ValueError("Unexpected replay results for the original archived Qwen output")
    packets = []
    mapping = []
    for i, (row, checked) in enumerate(
        zip(archived["cases"], replay["cases"], strict=True), start=1
    ):
        original = row["local_answer_artifact"]
        packet_id = f"R{i:02d}"
        packet = prepare_review_packet({
            "dataset": "m2-live-02/fictional_exposed_development",
            "query_id": packet_id,
            "result": original,
        })
        candidate = row["generated_candidate_raw"]
        if candidate is None:
            candidate = ""
        if packet["candidate_text"] != candidate:
            raise ValueError("Review packet did not preserve exact archived model draft")
        labels = [source["label"] for source in packet["sources"]]
        verified_v2 = validate_citations_v2(candidate, labels)
        if verified_v2.citation_contract_passed is not checked["citation_syntax_v2_counterfactual"]:
            raise ValueError("Experimental V2 syntax changed after the audited replay")
        packet["claims"] = _review_claims(candidate)
        packet["citation_gate"] = {
            "passed": verified_v2.citation_contract_passed,
            "count": verified_v2.citation_count,
            "invalid_labels": list(verified_v2.invalid_labels),
            "coverage": verified_v2.sentence_coverage,
            "parser": "opt_in_citation_v2_syntax_only",
            "note": "Citation syntax ONLY. No source entailment or task relevance inferred.",
        }
        packet["provenance"]["artifact_sha256"] = raw_sha256
        packet["provenance"]["artifact_filename"] = Path(ORIGINAL_EXPERIMENT_FILE).name
        packet["provenance"]["parser"] = "citation-v2-experimental-only"
        packet["research_boundary"] = {
            "model_generated_factual_candidate": row["model_calls"] > 0,
            "legacy_pipeline_publication_status": original["output_status"],
            "legacy_pipeline_abstained": original["abstained"],
            "replay_external_publications": 0,
            "review_packet_id_is_opaque": packet_id,
            "model_attempt_is_not_equal_to_pipeline_publication": True,
            "original_candidate_and_sources_already_exposed": True,
            "no_independent_quality_claim": True,
        }
        packet["instructions"] += [
            "Judge source relevance and claim support separately, ignoring syntactic citation acceptance.",
            "For rejected drafts, model attempted an answer even though the legacy pipeline abstained from publishing it.",
            "Use evidence sentence text (not citation labels) to assess factual entailment and contradictions.",
            "Do not assume source presence establishes answer sufficiency.",
            "The four fictional development cases were already inspected; this is a diagnostic review, not held-out quality.",
        ]
        summary = summarize_review_packet(packet)
        if (summary["review_status"] != "incomplete"
            or summary["fully_supported_claim_rate"] is not None
            or any(source["relevance"] != "unreviewed" for source in packet["sources"])
            or any(claim["support"] != "unreviewed" for claim in packet["claims"])
            or packet["review"]["expected_behavior"] != "unreviewed"):
            raise AssertionError("New review packet auto-labelled source or claim semantics")
        packets.append(packet)
        mapping.append({
            "packet_id": packet_id,
            "original_case_id": row["case_id"],
            "archived_pipeline_status": row["pipeline_output_status"],
            "source_count": len(packet["sources"]),
            "claim_count": len(packet["claims"]),
            "syntax_only_v2": packet["citation_gate"]["passed"],
            "semantic_status": "unreviewed",
        })
    manifest = {
        "schema_version": 1,
        "study_id": STUDY_ID,
        "source_report_sha256": raw_sha256,
        "source_prompt_sha256": replay["source_prompt_sha256"],
        "source_fixture_sha256": replay["source_fixture_sha256"],
        "source_parser_replay": replay["experiment_id"],
        "review_packet_count": len(packets),
        "model_calls_during_export": 0,
        "auto_semantic_labels_assigned": 0,
        "external_publications": 0,
        "quality_metrics": None,
        "cases_for_provenance_only_do_not_give_mapping_to_reviewer": mapping,
        "limitations": [
            "This is a previously inspected fictional development sample, NOT held-out TEST.",
            "Human review is optional and has NOT yet happened.",
            "Experimental citation syntax is not claim entailment.",
            "A legacy rejected draft is still a model answer attempt; only the pipeline blocked publication.",
            "Existing review-score's observed behavior describes pipeline publication, not model intent.",
            "Use independent training/development labels and adjudication for future M2 acceptance.",
        ],
    }
    return packets, manifest


def write_bundle(
    packets: list[dict[str, Any]], manifest: dict[str, Any], destination: Path
) -> bool:
    """Idempotent, do not change hand-labelled files or overwrite originals."""
    files = {
        destination / f"{i:02d}_review.json": json.dumps(packet, indent=2, ensure_ascii=False) + "\n"
        for i, packet in enumerate(packets, start=1)
    }
    files[destination / "manifest.json"] = json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
    if destination.exists() and any(destination.iterdir()):
        if set(destination.iterdir()) != set(files):
            raise FileExistsError("Existing review bundle contains other files; refusing changes")
        if any(path.read_text(encoding="utf-8") != content for path, content in files.items()):
            raise FileExistsError("Existing review bundle changed; refusing overwrite")
        return False
    destination.mkdir(parents=True, exist_ok=True)
    for path, content in files.items():
        with path.open("x", encoding="utf-8") as file:
            file.write(content)
    return True


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Export four unlabelled semantic review packets from saved M2 run; no model"
    )
    parser.add_argument("--original", default=ORIGINAL_EXPERIMENT_FILE)
    parser.add_argument("--output-dir", default="runs/m2-review02")
    opts = parser.parse_args()
    raw = Path(opts.original).read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    packets, manifest = make_review_packets(json.loads(raw), digest)
    created = write_bundle(packets, manifest, Path(opts.output_dir))
    print("M2_REVIEW02_UNLABELLED_BUNDLE_VERIFIED")
    print("M2_ORIGINAL_QWEN_SHA256=" + digest)
    print("M2_BUNDLE_STATE=" + ("CREATED" if created else "ALREADY_IDENTICAL"))
    print("M2_REVIEW_PACKETS=" + str(len(packets)))
    for entry in manifest["cases_for_provenance_only_do_not_give_mapping_to_reviewer"]:
        print(
            "M2_PACKET=" + entry["packet_id"]
            + " SOURCES=" + str(entry["source_count"])
            + " CLAIMS=" + str(entry["claim_count"])
            + " EXPERIMENTAL_CITATION_VALID=" + str(entry["syntax_only_v2"])
            + " SEMANTIC=UNREVIEWED"
        )
    print("M2_REVIEW_BUNDLE=" + str(opts.output_dir))
    print("MODEL_CALLS=0; EXTERNAL_PUBLICATIONS=0; HELD_OUT_SCORE=NONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
