"""M2-LIVE-02: versioned prompt-only Qwen development control.

Reads exact earlier M2-LIVE-01 report, never reuses it as an evaluation set.
RAGPipeline and the citation validator are unchanged. All model outputs are
quarantined, including syntax-valid claims, until separate semantic review.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from raglab.context import ContextBuilder
from raglab.evaluation.m2_live_audit import audit_saved_m2
from raglab.evaluation.m2_live_smoke import (
    DOCUMENTS, MODEL_ID, SCENARIOS, FixedEvidenceRetriever, fixture_sha256,
)
from raglab.generation import LocalTransformersGenerator
from raglab.rag import RAGPipeline

EXPERIMENT_ID = "M2-LIVE-02-PROMPT-ONLY-DEVELOPMENT"
ORIGINAL_REPORT_SHA256 = "bd3b35354442062a861c8ed6d4d3b49f58c3ea185a5df7321728c34ef21ed3d8"
ABSTENTION_MARKER = "INSUFFICIENT_EVIDENCE"
SYSTEM_PROMPT_V2 = """You answer ONLY from the provided, labelled evidence.

You have exactly two allowed response forms:
A) If the available evidence explicitly answers the question, output ONE short
   factual sentence ending with its exact source citation: [S1] or [S2].
   Cite each factual sentence. Use only source labels that appear under Evidence.
B) If evidence does not answer the question, mentions unrelated entities,
   or two sources directly disagree on the requested fact, output EXACTLY:
INSUFFICIENT_EVIDENCE

Do not guess, improvise, silently choose between conflicting facts,
or convert a document about another object into an answer about this one.
Do not output ANSWER:, markdown, explanations, or extra text.

Examples with imaginary documents NOT used in the questions below:

Question: Who made the Cedar Beacon?
Evidence:
[S1]
text: The Cedar Beacon was created by Atlas Research.
Response: Atlas Research created the Cedar Beacon [S1].

Question: Who made the Cedar Beacon?
Evidence:
[S1]
text: The Forest Camera was created by Zephyr Labs.
Response: INSUFFICIENT_EVIDENCE

Question: When did the Cedar Beacon launch?
Evidence:
[S1]
text: The Cedar Beacon launched in 2014.
[S2]
text: The Cedar Beacon launched in 2019.
Response: INSUFFICIENT_EVIDENCE

Read the question and evidence below, then obey form A or B exactly."""
PROMPT_VERSION = "m2-v02-cited-or-abstain-v1"
MAX_NEW_TOKENS = 128


def prompt_sha256() -> str:
    return hashlib.sha256(
        json.dumps(
            {
                "prompt_version": PROMPT_VERSION,
                "system_prompt": SYSTEM_PROMPT_V2,
                "marker": ABSTENTION_MARKER,
                "max_new_tokens": MAX_NEW_TOKENS,
            },
            sort_keys=True, ensure_ascii=False, separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


class VersionedPromptAdapter:
    """Real-model interface: change instructions, never append citations."""

    def __init__(self, generator: Any) -> None:
        if not hasattr(generator, "generate") or not isinstance(
            getattr(generator, "name", None), str
        ):
            raise ValueError("Expected named existing local generator")
        self.inner = generator
        self.name = "experiment:" + PROMPT_VERSION + ":" + generator.name
        self.calls = 0

    def generate(
        self, *, system_prompt: str, user_prompt: str, max_new_tokens: int
    ) -> str:
        self.calls += 1
        # Use the same actual V2 pipeline evidence/context string. Only the
        # system instruction changes, and the raw model text is untouched.
        return self.inner.generate(
            system_prompt=SYSTEM_PROMPT_V2,
            user_prompt=user_prompt + "\n\nResponse (one cited sentence OR INSUFFICIENT_EVIDENCE):",
            max_new_tokens=max_new_tokens,
        )


def read_sealed_baseline(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != ORIGINAL_REPORT_SHA256:
        raise ValueError("M2-LIVE-01 baseline JSON SHA256 differs from audited original")
    report = json.loads(raw)
    audit = audit_saved_m2(report, digest)
    if (
        audit["audit_status"] != "PASS_NO_NEW_MODEL_RUN"
        or audit["total_generator_calls"] != 3
        or set(audit["status_counts"]) != {
            "rejected_citation_contract", "abstained_no_context"
        }
        or audit["status_counts"]["rejected_citation_contract"] != 3
    ):
        raise ValueError("Original M2-LIVE-01 audit provenance changed")
    return {
        "original_sha256": digest,
        "original_fixture_sha256": audit["fixture_sha256"],
        "original_model_id": audit["model_id"],
        "original_status_counts": audit["status_counts"],
    }


def run_development_controls(inner: Any) -> dict[str, Any]:
    """One new versioned pass on KNOWN fictional development controls.

    This is not held-out validation. No evidence labels pass into a claim
    verifier; citation syntax is a separate recorded contract property.
    """
    adapter = VersionedPromptAdapter(inner)
    rows = []
    for spec in SCENARIOS:
        retriever = FixedEvidenceRetriever(spec["source_ids"])
        pipeline = RAGPipeline(
            documents=DOCUMENTS,
            retriever=retriever,
            context_builder=ContextBuilder(max_chars=3500, per_source_chars=1200),
            generator=adapter,
            top_k=3,
            max_new_tokens=MAX_NEW_TOKENS,
        )
        pipeline.index()
        before = adapter.calls
        response = pipeline.answer(spec["question"])
        actual_calls = adapter.calls - before
        if actual_calls != int(bool(spec["source_ids"])):
            raise AssertionError("Unexpected model invocation count")
        if [s.doc_id for s in response.sources] != spec["source_ids"]:
            raise AssertionError("The source provenance was modified")
        draft = response.raw_generation
        if draft is None and response.output_status == "accepted":
            draft = response.answer
        if spec["source_ids"] and not isinstance(draft, str):
            raise AssertionError("Generated candidate text not recorded")
        declared_abstention = (
            isinstance(draft, str) and draft.strip() == ABSTENTION_MARKER
        )
        if not spec["source_ids"]:
            if (
                response.output_status != "abstained_no_context"
                or response.timings_ms["generation"] != 0
                or actual_calls
            ):
                raise AssertionError("No-context must skip Qwen")
            hold_reason = "NO_CONTEXT_NO_GENERATION"
        elif declared_abstention:
            # RAGPipeline correctly does not accept an uncited marker.
            # Research classification does not promote that marker into
            # unverified general-purpose semantic abstention.
            if response.output_status != "rejected_citation_contract":
                raise AssertionError("Uncited marker unexpectedly published")
            hold_reason = "MODEL_DECLARED_INSUFFICIENT_EVIDENCE_UNVERIFIED"
        elif response.output_status == "accepted":
            # The underlying RAGPipeline syntactic gate accepts it, but
            # the experiment does not publish any candidate fact.
            hold_reason = "CITATION_SYNTAX_ACCEPTED_HELD_FOR_SEMANTIC_REVIEW"
        else:
            hold_reason = "CITATION_SYNTAX_REJECTED_HELD"
        rows.append({
            "case_id": spec["case_id"],
            "curated_condition_not_model_inferred": spec["evidence_condition"],
            "curated_expectation_not_a_score": spec["expected_behavior"],
            "model_calls": actual_calls,
            "original_source_ids": list(spec["source_ids"]),
            "pipeline_output_status": response.output_status,
            "citation_syntax_passed": response.citation_report.citation_contract_passed,
            "model_declared_exact_abstention": declared_abstention,
            "research_publication_decision": hold_reason,
            "published_to_external_system": False,
            "semantic_entailment": "NOT_EVALUATED",
            "task_alignment": "NOT_EVALUATED",
            "abstention_appropriateness": "NOT_EVALUATED",
            "generated_candidate_raw": draft,
            "local_answer_artifact": response.to_dict(),
        })
    if adapter.calls != 3:
        raise AssertionError("M2-LIVE-02 is capped at exactly three model calls")
    config = getattr(getattr(inner, "_model", None), "config", None)
    resolved = getattr(config, "_commit_hash", None)
    return {
        "schema_version": 1,
        "experiment_id": EXPERIMENT_ID,
        "status": "versioned_prompt_development_not_independent_semantic_evaluation",
        "prompt_version": PROMPT_VERSION,
        "prompt_sha256": prompt_sha256(),
        "model_id": MODEL_ID if isinstance(inner, LocalTransformersGenerator) else inner.name,
        "model_revision_if_resolved": resolved if isinstance(resolved, str) else None,
        "decoding": "greedy_do_sample_false",
        "max_new_tokens": MAX_NEW_TOKENS,
        "fixture_sha256": fixture_sha256(),
        "source_policy": "identical_fixed_fictional_development_sources_as_M2_LIVE01",
        "generator_calls": adapter.calls,
        "case_count": len(rows),
        "pipeline_status_counts": dict(Counter(r["pipeline_output_status"] for r in rows)),
        "publication_policy": "ALL_OUTPUTS_RESEARCH_ONLY_HELD_FOR_SEMANTIC_REVIEW",
        "cases": rows,
        "limitations": [
            "The four fictional cases are explicitly already-exposed development controls.",
            "This is a versioned prompt experiment, not a fresh held-out semantic benchmark.",
            "Syntactically cited false claims remain possible and are never published by this harness.",
            "A model-declared insufficient-evidence marker is not independently verified.",
            "RAGPipeline's original citation fail-closed contract is unchanged.",
            "Model revision may be unresolved; do not call this a pinned generator benchmark.",
            "No automatic source relevance, contradiction truth or answer correctness score.",
        ],
    }


def render_report(result: dict[str, Any]) -> str:
    lines = [
        "# M2-LIVE-02 — Prompt-only development run",
        "",
        "Version: " + result["prompt_version"],
        "Prompt SHA256: " + result["prompt_sha256"],
        "Prior M2-LIVE-01 SHA256: " + result["baseline_report_sha256"],
        "",
        "| Control | Pipeline status | Citation syntax | Model abstention | Research disposition |",
        "|---|---|---|---|---|",
    ]
    for row in result["cases"]:
        lines.append(
            f"| {row['case_id']} | {row['pipeline_output_status']} | "
            f"{row['citation_syntax_passed']} | "
            f"{row['model_declared_exact_abstention']} | "
            f"{row['research_publication_decision']} |"
        )
    lines += ["", "## Evaluation boundaries", ""]
    lines += ["- " + x for x in result["limitations"]]
    lines += ["", "No semantic quality score or independent validation is claimed.", ""]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run a single new versioned M2 prompt development smoke"
    )
    parser.add_argument(
        "--original",
        default="runs/m2-live/M2_LIVE_20261104T182515461187Z.json",
    )
    parser.add_argument("--output-dir", default="runs/m2-live-v2")
    options = parser.parse_args()
    folder = Path(options.output_dir)
    if folder.exists() and list(folder.glob("M2_LIVE02_*.json")):
        raise FileExistsError("M2-LIVE-02 already recorded; refusing a repeated run")
    original = read_sealed_baseline(Path(options.original))
    generator = LocalTransformersGenerator(MODEL_ID)
    result = run_development_controls(generator)
    result["baseline_report_sha256"] = original["original_sha256"]
    result["created_utc"] = datetime.now(UTC).isoformat()
    folder.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    output = folder / f"M2_LIVE02_{stamp}.json"
    markdown = folder / f"M2_LIVE02_{stamp}.md"
    with output.open("x", encoding="utf-8") as writer:
        json.dump(result, writer, ensure_ascii=False, indent=2)
    with markdown.open("x", encoding="utf-8") as writer:
        writer.write(render_report(result))
    print("M2_LIVE02_VERSIONED_DEVELOPMENT_RUN_COMPLETE")
    print("M2_V2_PROMPT_SHA256=" + result["prompt_sha256"])
    print("M2_V2_FIXTURE_SHA256=" + result["fixture_sha256"])
    print("M2_V2_BASELINE_SHA256=" + result["baseline_report_sha256"])
    print("M2_V2_MODEL_REVISION=" + str(result["model_revision_if_resolved"]))
    print("M2_V2_MODEL_CALLS=" + str(result["generator_calls"]))
    for row in result["cases"]:
        print("M2_V2_CASE=" + row["case_id"])
        print("PIPELINE_STATUS=" + row["pipeline_output_status"])
        print("SYNTAX_CITATIONS_VALID=" + str(row["citation_syntax_passed"]))
        print("MODEL_DECLARED_ABSTENTION=" + str(row["model_declared_exact_abstention"]))
        print("RESEARCH_DISPOSITION=" + row["research_publication_decision"])
        if row["model_calls"]:
            print("RAW_DRAFT_JSON=" + json.dumps(
                row["generated_candidate_raw"][:1800], ensure_ascii=False
            ))
        else:
            print("GENERATOR_SKIPPED=true")
    print("M2_V2_LOCAL_JSON=" + str(output))
    print("M2_V2_LOCAL_MARKDOWN=" + str(markdown))
    print("ANSWER_CORRECTNESS=NOT_EVALUATED; EXTERNAL_PUBLICATION=NONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
