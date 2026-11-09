"""One-pass, checkpointed M2 synthetic-template Qwen control run.

The inference input never contains expected literals or category labels. The
result is a narrow programmatic template check, not a semantic evaluator.
Everything remains gitignored/local. The default RAGPipeline is unchanged.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import asdict
from pathlib import Path
from typing import Any

from raglab.evaluation.m2_synth_protocol import (
    EXPECTED_CASES_SHA256, MODEL_ID, PROMPT_SHA256, STUDY_ID,
    aggregate_controls, canonical_sha256, score_observation, validate_protocol,
)


def manifest_payload() -> dict[str, Any]:
    cases = validate_protocol()
    return {
        "schema_version": 1,
        "study_id": STUDY_ID,
        "run_type": "one_pass_programmatic_synthetic_controls_not_semantic_truth",
        "cases_sha256": EXPECTED_CASES_SHA256,
        "prompt_sha256": PROMPT_SHA256,
        "model_id": MODEL_ID,
        "frozen_case_count": len(cases),
        "cases": cases,
        "source_label_policy": "RAGPipeline ContextBuilder S1/S2 fixed source order",
        "source_policy": "fixed_fictional_local_documents_no_retrieval_metrics",
        "allowed_model_calls": 18,
        "generation_config": "existing_M2_LIVE02_prompt_greedy_128_tokens",
        "source_content_license": "original_fictional_test_material",
        "hold_all_generated_text": True,
        "external_publication": False,
        "known_limits": [
            "Novel invented entities, but same task template family: not open-domain answer quality.",
            "Programmatic gold is by construction, not expert-labelled natural-language truth.",
            "Answerable class metric uses reference literal plus citation-syntax proxy, not entailment.",
            "Previously exposed four cases and SciFact TEST qrels are not queried.",
            "Model revision may not be pinned by the existing local transformer loader.",
            "Zero inference on six no-context cases does not evaluate semantic abstention.",
        ],
    }


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def write_or_check(path: Path, data: Any) -> bool:
    """Return True on new creation only. Never overwrite existing research data."""
    body = _canonical_json(data)
    if path.exists():
        if path.read_text(encoding="utf-8") != body:
            raise FileExistsError("Existing frozen research file differs: " + str(path))
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        handle.write(body)
    return True


def _model_revision(generator: Any) -> str | None:
    config = getattr(getattr(generator, "_model", None), "config", None)
    revision = getattr(config, "_commit_hash", None)
    return revision if isinstance(revision, str) else None


def run_case(case: dict[str, Any], generator: Any) -> dict[str, Any]:
    from raglab.citations import validate_citations
    from raglab.citations.validator_v2 import validate_citations_v2
    from raglab.context import ContextBuilder
    from raglab.core import Document
    from raglab.evaluation.m2_live_smoke import FixedEvidenceRetriever
    from raglab.rag import RAGPipeline

    sources = case["sources"]
    documents = [Document(doc["id"], doc["text"], doc["title"]) for doc in sources]
    ids = [doc["id"] for doc in sources]
    retriever = FixedEvidenceRetriever(ids)
    pipeline = RAGPipeline(
        documents=documents,
        retriever=retriever,
        context_builder=ContextBuilder(max_chars=3500, per_source_chars=1200),
        generator=generator,
        top_k=3,
        max_new_tokens=128,
    )
    pipeline.index()
    before = generator.calls
    result = pipeline.answer(case["question"])
    calls = generator.calls - before
    if calls != int(bool(sources)):
        raise AssertionError("Model calls differ from frozen control")
    observed_ids = [src.doc_id for src in result.sources]
    if observed_ids != ids:
        raise AssertionError("Source order differs from frozen documents")
    for generated, original in zip(result.sources, sources, strict=True):
        if generated.text != original["text"] or generated.title != original["title"]:
            raise AssertionError("Model context differs from frozen evidence")
    raw = result.raw_generation if result.raw_generation is not None else (
        result.answer if result.output_status == "accepted" else None
    )
    if not sources:
        if (raw is not None or result.output_status != "abstained_no_context"
            or result.timings_ms["generation"] != 0):
            raise AssertionError("No-context generator-skip contract broken")
    elif not isinstance(raw, str):
        raise AssertionError("Original generated candidate is missing")
    labels = [src.label for src in result.sources]
    candidate_text = raw if raw is not None else result.answer
    legacy = validate_citations(candidate_text, labels)
    experimental = validate_citations_v2(candidate_text, labels)
    if result.citation_report != legacy:
        raise AssertionError("Original pipeline citation report differs")
    return {
        "case_id": case["case_id"],
        "case_sha256": canonical_sha256(case),
        "source_ids": ids,
        "model_calls": calls,
        "raw_candidate": raw,
        "pipeline_status": result.output_status,
        "syntax_v1_pass": legacy.citation_contract_passed,
        "syntax_v2_pass": experimental.citation_contract_passed,
        "syntax_v2_report": asdict(experimental),
        "sent_to_external_system": False,
        "observed_generator_name": generator.name,
        "model_revision_if_resolved": _model_revision(getattr(generator, "inner", generator)),
        "original_answer_artifact": result.to_dict(),
        "semantic_support_assessed": False,
        "task_relevance_assessed": False,
    }


def verify_record(case: dict[str, Any], record: dict[str, Any]) -> dict[str, Any]:
    """Recheck local saved row before its score or resume is trusted."""
    from raglab.citations import validate_citations
    from raglab.citations.validator_v2 import validate_citations_v2

    if (record.get("case_sha256") != canonical_sha256(case)
        or record.get("case_id") != case["case_id"]
        or record.get("source_ids") != [doc["id"] for doc in case["sources"]]
        or record.get("sent_to_external_system") is not False
        or record.get("semantic_support_assessed") is not False
        or record.get("task_relevance_assessed") is not False):
        raise ValueError("Saved provenance, quarantine or semantic boundaries changed")
    artifact = record.get("original_answer_artifact")
    if not isinstance(artifact, dict) or artifact.get("output_status") != record.get("pipeline_status"):
        raise ValueError("Saved original pipeline response is absent or modified")
    if artifact.get("question") != case["question"]:
        raise ValueError("Saved question differs from frozen case")
    saved_sources = artifact.get("sources")
    if not isinstance(saved_sources, list) or len(saved_sources) != len(case["sources"]):
        raise ValueError("Source set differs from frozen case")
    for i, (source, ref) in enumerate(zip(saved_sources, case["sources"], strict=True), start=1):
        if (source.get("label") != f"S{i}" or source.get("doc_id") != ref["id"]
            or source.get("title") != ref["title"] or source.get("text") != ref["text"]):
            raise ValueError("Evidence mapping differs from frozen source")
    original = (artifact.get("raw_generation") if artifact.get("raw_generation") is not None
                else artifact.get("answer") if artifact.get("output_status") == "accepted" else None)
    if original != record.get("raw_candidate"):
        raise ValueError("Saved raw candidate differs from original pipeline response")
    labels = [f"S{i}" for i in range(1, len(saved_sources) + 1)]
    text = original if original is not None else artifact["answer"]
    v1 = validate_citations(text, labels)
    v2 = validate_citations_v2(text, labels)
    if (record.get("syntax_v1_pass") is not v1.citation_contract_passed
        or record.get("syntax_v2_pass") is not v2.citation_contract_passed
        or canonical_sha256(record.get("syntax_v2_report")) != canonical_sha256(asdict(v2))):
        raise ValueError("Saved citation results differ from re-evaluation")
    status = record.get("pipeline_status")
    if case["category"] == "no_context":
        if (status != "abstained_no_context" or artifact.get("abstained") is not True
            or artifact.get("raw_generation") is not None):
            raise ValueError("No-context refusal differs")
    elif status == "accepted":
        if not v1.citation_contract_passed or artifact.get("abstained") is not False:
            raise ValueError("A citation-invalid answer was accepted")
    elif status == "rejected_citation_contract":
        if (v1.citation_contract_passed or artifact.get("abstained") is not True
            or artifact.get("answer") != (
                "The generated draft failed the citation requirements; "
                "no factual answer is being provided."
            )):
            raise ValueError("Unapproved factual answer escaped the gate")
    else:
        raise ValueError("Unexpected pipeline publication status")
    return score_observation(case, record)


def build_final_report(cases: list[dict[str, Any]], records: list[dict[str, Any]]) -> dict[str, Any]:
    if len(records) != len(cases):
        raise ValueError("Final report requires every frozen case")
    scores = [verify_record(case, row) for case, row in zip(cases, records, strict=True)]
    report = aggregate_controls(scores)
    revisions = {row.get("model_revision_if_resolved") for row in records
                 if row.get("model_revision_if_resolved") is not None}
    if len(revisions) > 1:
        raise ValueError("Saved model revisions differ between cases")
    report.update({
        "report_schema_version": 1,
        "status": "SYNTHETIC_TEMPLATE_CONTROLS_NOT_SEMANTIC_TRUTH",
        "model_id": MODEL_ID,
        "model_revision_if_resolved": next(iter(revisions), None),
        "model_calls": sum(row["model_calls"] for row in records),
        "publication_actions": 0,
        "original_pipeline_behavior_unchanged": True,
        "all_generated_candidates_quarantined": True,
        "case_scores": scores,
        "source_record_sha256": [canonical_sha256(row) for row in records],
        "status_counts": dict(Counter(row["pipeline_status"] for row in records)),
        "sample_size_warning": "6 cases per category; no broad model-quality inference warranted",
    })
    if report["model_calls"] != 18:
        raise AssertionError("Unexpected total model calls")
    return report


def run_local(output_dir: Path, generator: Any | None = None) -> dict[str, Any]:
    from raglab.evaluation.m2_live_v2 import VersionedPromptAdapter, prompt_sha256
    if prompt_sha256() != PROMPT_SHA256:
        raise ValueError("Frozen existing M2-LIVE-02 prompt has changed")
    cases = validate_protocol()
    output_dir.mkdir(parents=True, exist_ok=True)
    write_or_check(output_dir / "manifest.json", manifest_payload())
    paths = [output_dir / "cases" / f"{i+1:02d}.json" for i in range(len(cases))]
    if any(not path.exists() for path in paths):
        if generator is None:
            from raglab.generation import LocalTransformersGenerator
            generator = LocalTransformersGenerator(MODEL_ID)
        adapter = VersionedPromptAdapter(generator)
        for i, (case, path) in enumerate(zip(cases, paths, strict=True), start=1):
            if path.exists():
                verify_record(case, json.loads(path.read_text(encoding="utf-8")))
                continue
            record = run_case(case, adapter)
            score = verify_record(case, json.loads(json.dumps(record)))
            write_or_check(path, record)
            print(f"M2_SYNTH_PROGRESS={i}/24 CATEGORY={case['category']} "
                  f"STATUS={record['pipeline_status']} CONTROL_PASS={score['control_success']}", flush=True)
    records = [json.loads(path.read_text(encoding="utf-8")) for path in paths]
    report = build_final_report(cases, records)
    write_or_check(output_dir / "report.json", report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="One-pass local Qwen synthetic source-controls")
    parser.add_argument("--output-dir", default="runs/m2-synth01")
    args = parser.parse_args()
    result = run_local(Path(args.output_dir))
    print("M2_SYNTH01_COMPLETE_AND_ARCHIVED")
    print("M2_SYNTH01_CASES_SHA256=" + result["source_cases_sha256"])
    print("M2_SYNTH01_MODEL_CALLS=" + str(result["model_calls"]))
    print("M2_SYNTH01_PRIMARY_CONTROL_PROXY=" + str(result["primary_control_success_rate"]))
    for category, data in result["by_category"].items():
        print(f"M2_SYNTH01_CATEGORY={category} COUNT={data['n']} "
              f"PASS={data['success_count']} "
              f"SYNTAX_V2={data['experimental_syntax_pass_count']} "
              f"ABSTAIN_MARKER={data['model_declared_abstention_count']}")
    print("M2_SYNTH01_REPORT=" + str(Path(args.output_dir) / "report.json"))
    print("M2_SEMANTIC_TRUTH=NOT_EVALUATED; EXTERNAL_PUBLICATION=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
