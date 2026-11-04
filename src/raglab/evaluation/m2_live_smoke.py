"""M2-LIVE-01: bounded real-generator smoke on original synthetic evidence.

An operational smoke, NOT an independent answer-quality benchmark.
All factual texts and expected behavior are original fictional controls.
Only syntax/provenance/status are automatically evaluated; support and
task correctness remain NOT_EVALUATED until independent review.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from raglab.context import ContextBuilder
from raglab.core import Document, SearchResult
from raglab.generation import LocalTransformersGenerator
from raglab.rag import RAGPipeline

MODEL_ID = "Qwen/Qwen2.5-0.5B-Instruct"
EXPERIMENT_ID = "M2-LIVE-GROUNDED-CONTROLS-01"

DOCUMENTS: tuple[Document, ...] = (
    Document(
        "fiction-orion", "The Orion Navigation System used by the Aster Rover "
        "was developed by Meridian Robotics.", "Orion Navigation technical record"
    ),
    Document(
        "fiction-solis", "The Solis Probe uses an optical navigation sensor "
        "manufactured by Helios Instruments.", "Solis Probe equipment log"
    ),
    Document(
        "fiction-zenith-a", "The Zenith Probe launched on June 4, 2020.",
        "Zenith Probe launch note A"
    ),
    Document(
        "fiction-zenith-b", "The Zenith Probe launched on July 9, 2021.",
        "Zenith Probe launch note B"
    ),
)
QUESTION = "Which company developed the Orion Navigation System used by the Aster Rover?"
SCENARIOS: tuple[dict[str, Any], ...] = (
    {
        "case_id": "answerable_supplied_evidence",
        "question": QUESTION,
        "source_ids": ["fiction-orion"],
        "expected_behavior": "answer",
        "reference_phrase": "Meridian Robotics",
        "evidence_condition": "curated_adequate",
    },
    {
        "case_id": "irrelevant_nonempty_evidence",
        "question": QUESTION,
        "source_ids": ["fiction-solis"],
        "expected_behavior": "abstain",
        "reference_phrase": None,
        "evidence_condition": "curated_irrelevant",
    },
    {
        "case_id": "contradictory_evidence",
        "question": "On what date did the Zenith Probe launch?",
        "source_ids": ["fiction-zenith-a", "fiction-zenith-b"],
        "expected_behavior": "abstain_or_explicit_conflict",
        "reference_phrase": None,
        "evidence_condition": "curated_conflicting",
    },
    {
        "case_id": "empty_retrieval",
        "question": QUESTION,
        "source_ids": [],
        "expected_behavior": "abstain",
        "reference_phrase": None,
        "evidence_condition": "no_context",
    },
)


class FixedEvidenceRetriever:
    """Fixed, source-ID-valid control; does not claim retrieval benchmark scores."""

    name = "fixed_control_evidence_not_retrieval_benchmark"

    def __init__(self, source_ids: list[str]) -> None:
        self.source_ids = source_ids.copy()
        self.known: set[str] | None = None

    def index(self, documents: list[Document]) -> None:
        self.known = {d.id for d in documents}
        if not set(self.source_ids).issubset(self.known):
            raise ValueError("Synthetic case requested an unknown source")

    def retrieve(self, query: str, k: int) -> list[SearchResult]:
        if self.known is None:
            raise RuntimeError("Fixed evidence retriever was not indexed")
        if k < 1:
            raise ValueError("top_k must be positive")
        return [
            SearchResult(doc_id=doc_id, score=1.0, rank=i)
            for i, doc_id in enumerate(self.source_ids[:k], start=1)
        ]


class CountingGenerator:
    def __init__(self, inner: Any) -> None:
        self.inner = inner
        self.name = inner.name
        self.calls = 0

    def generate(self, *, system_prompt: str, user_prompt: str, max_new_tokens: int) -> str:
        self.calls += 1
        return self.inner.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_new_tokens=max_new_tokens,
        )


def fixture_sha256() -> str:
    manifest = {
        "documents": [{"id": d.id, "title": d.title, "text": d.text} for d in DOCUMENTS],
        "scenarios": list(SCENARIOS),
    }
    return hashlib.sha256(
        json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def run_control_cases(generator: Any) -> dict[str, Any]:
    if not hasattr(generator, "generate") or not isinstance(getattr(generator, "name", None), str):
        raise ValueError("Expected a named generator with a generate method")
    counter = CountingGenerator(generator)
    output = []
    for case in SCENARIOS:
        retrieval = FixedEvidenceRetriever(case["source_ids"])
        pipeline = RAGPipeline(
            documents=DOCUMENTS,
            retriever=retrieval,
            context_builder=ContextBuilder(max_chars=3500, per_source_chars=1200),
            generator=counter,
            top_k=3,
            max_new_tokens=128,
        )
        pipeline.index()
        before = counter.calls
        answer = pipeline.answer(case["question"])
        calls = counter.calls - before
        if calls != int(bool(case["source_ids"])):
            raise AssertionError("Generator call count differs from supplied-context contract")
        if [s.doc_id for s in answer.sources] != case["source_ids"]:
            raise AssertionError("Evidence provenance differs from predeclared fixture")
        report = answer.citation_report
        if answer.output_status == "accepted" and not report.citation_contract_passed:
            raise AssertionError("Public answer passed despite citation failure")
        if case["case_id"] == "empty_retrieval" and (
            answer.output_status != "abstained_no_context" or answer.timings_ms["generation"] != 0
        ):
            raise AssertionError("No-context control did not skip the model and abstain")

        phrase = case["reference_phrase"]
        text_has_reference = (
            bool(re.search(re.escape(phrase), answer.answer, flags=re.IGNORECASE))
            if phrase is not None else None
        )
        output.append({
            "case_id": case["case_id"],
            "evidence_condition_curated_not_model_inferred": case["evidence_condition"],
            "expected_behavior_fictional_control": case["expected_behavior"],
            "reference_phrase_present_in_public_answer": text_has_reference,
            "generator_calls": calls,
            "output_status": answer.output_status,
            "safe_publication_gate_passed": answer.output_status != "accepted"
                or report.citation_contract_passed,
            "citation_contract_syntax_passed": report.citation_contract_passed,
            "semantic_support": "not_evaluated",
            "task_correctness": "not_evaluated",
            "expected_behavior_alignment": "not_evaluated_requires_independent_review",
            "local_answer_artifact": answer.to_dict(),
        })
    if counter.calls != 3:
        raise AssertionError("Only three of four controls may call the local generator")
    model_config = getattr(getattr(generator, "_model", None), "config", None)
    model_commit = getattr(model_config, "_commit_hash", None)
    return {
        "schema_version": 1,
        "experiment_id": EXPERIMENT_ID,
        "status": "operational_synthetic_controls_not_semantic_quality_benchmark",
        "model_id": MODEL_ID if isinstance(generator, LocalTransformersGenerator) else generator.name,
        "resolved_model_commit_if_available": model_commit if isinstance(model_commit, str) else None,
        "generation_policy": "model_greedy_decode_do_sample_false",
        "fixture_sha256": fixture_sha256(),
        "fixture_license": "original_fictional_test_material",
        "source_selection": "fixed_original_source_ids_not_retriever_evaluation",
        "case_count": len(output),
        "total_generator_calls": counter.calls,
        "status_counts": dict(Counter(item["output_status"] for item in output)),
        "cases": output,
        "assessment_boundaries": [
            "A syntactically valid citation is NOT semantic support or answer relevance.",
            "Reference phrase matching is a smoke diagnostic, NOT a scientific answer correctness metric.",
            "Irrelevant nonempty evidence is intentionally NOT filtered by a calibrated semantic gate.",
            "A rejected citation draft is NOT evidence of an informed semantic abstention.",
            "The contradictory examples are synthetic and their correct handling needs separate review.",
            "Qwen sampling is disabled, but model revision may not resolve to a pinned commit.",
            "This fixed-evidence control does not evaluate retrieval precision or end-to-end RAG.",
            "Original fictional controls are not an independently held-out test dataset.",
        ],
    }


def summary_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# M2-LIVE-01 — Real-model synthetic evidence controls",
        "",
        f"Operational status: {report['status']}",
        f"Model: {report['model_id']} (resolved SHA: {report['resolved_model_commit_if_available']})",
        f"Fixture SHA256: {report['fixture_sha256']}",
        "",
        "| Control | Condition | Expected | Output status | Generator calls | Citation gate |",
        "|---|---|---|---|---:|---|",
    ]
    for case in report["cases"]:
        lines.append(
            f"| {case['case_id']} | {case['evidence_condition_curated_not_model_inferred']} | "
            f"{case['expected_behavior_fictional_control']} | {case['output_status']} | "
            f"{case['generator_calls']} | "
            f"{case['citation_contract_syntax_passed']} |"
        )
    lines += [
        "", "## Result boundaries", "",
        *["- " + note for note in report["assessment_boundaries"]],
        "",
        "All original generated text and source passages remain in local gitignored run artifacts.",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(
        description="Run bounded real Qwen citation/abstention smoke on fictional controls"
    )
    parser.add_argument("--output-dir", default="runs/m2-live")
    args = parser.parse_args()
    directory = Path(args.output_dir)
    if directory.exists() and list(directory.glob("M2_LIVE_*.json")):
        raise FileExistsError(
            "M2 real-model control has already run; refusing silent rerun or output replacement"
        )
    generator = LocalTransformersGenerator(MODEL_ID)
    result = run_control_cases(generator)
    result["created_utc"] = datetime.now(UTC).isoformat()
    directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    json_file = directory / f"M2_LIVE_{stamp}.json"
    md_file = directory / f"M2_LIVE_{stamp}.md"
    with json_file.open("x", encoding="utf-8") as file:
        json.dump(result, file, ensure_ascii=False, indent=2)
    with md_file.open("x", encoding="utf-8") as file:
        file.write(summary_markdown(result))
    print("M2_LIVE_SYNTHETIC_SMOKE_COMPLETE")
    print(f"M2_FIXTURE_SHA256={result['fixture_sha256']}")
    print(f"M2_QWEN_RESOLVED_COMMIT={result['resolved_model_commit_if_available']}")
    print(f"M2_CASES={result['case_count']}")
    print(f"M2_GENERATOR_CALLS={result['total_generator_calls']}")
    for case in result["cases"]:
        print(f"M2_CASE={case['case_id']} STATUS={case['output_status']} "
              f"CITATIONS_VALID={case['citation_contract_syntax_passed']}")
    print(f"M2_RAW_JSON_LOCAL={json_file}")
    print(f"M2_REPORT_LOCAL={md_file}")
    print("SEMANTIC_SUPPORT=NOT_EVALUATED; ANSWER_CORRECTNESS=NOT_EVALUATED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
