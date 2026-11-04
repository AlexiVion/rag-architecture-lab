"""M2-GUARD-DEV-01: scoped fail-closed evidence consistency controls.

No Qwen, no independent model-quality accuracy estimate, no publication.
"""
from __future__ import annotations

from raglab.context import ContextBuilder
from raglab.core import Document
from raglab.evaluation.m2_guard_dev01 import (
    assess_candidate, assess_evidence, make_research_evidence_gate,
)
from raglab.evaluation.m2_synth_protocol import validate_protocol
from raglab.evaluation.m2_live_smoke import FixedEvidenceRetriever
from raglab.rag import RAGPipeline


QUESTION = "Which company developed the Pulsar Guidance Node installed on the Arden Crawler?"
VALID = {"id": "record-1", "text": "The Pulsar Guidance Node installed on the Arden Crawler was developed by Thornwood Automation."}
FOIL = {"id": "record-2", "text": "The Gale Optical Sensor installed on the Vesper Drone was developed by Oxbow Devices."}
OTHER = {"id": "record-3", "text": "The Pulsar Guidance Node installed on the Arden Crawler was developed by Bluepeak Science."}


def test_exact_matching_evidence_allows_only_explicit_single_consistent_relation():
    good = assess_evidence(QUESTION, [VALID])
    assert good.allow_generation
    assert good.company == "Thornwood Automation"
    assert good.supporting_labels == ("S1",)
    same = assess_evidence(QUESTION, [VALID, {**VALID, "id": "record-9"}])
    assert same.allow_generation
    assert same.supporting_labels == ("S1", "S2")
    assert assess_evidence(QUESTION, []).reason == "DENY_NO_CONTEXT"


def test_conflicting_irrelevant_and_unknown_grammars_fail_closed():
    assert assess_evidence(QUESTION, [FOIL]).reason == "DENY_SOURCE_OFF_TARGET"
    assert assess_evidence(QUESTION, [VALID, OTHER]).reason == "DENY_SOURCE_CONTRADICTION"
    assert assess_evidence(QUESTION, [VALID, FOIL]).reason == "DENY_SOURCE_OFF_TARGET"
    assert assess_evidence("Who made it?", [VALID]).reason == "DENY_UNSUPPORTED_QUESTION_GRAMMAR"
    assert assess_evidence(QUESTION, [{"id": "x", "text": "Maybe Thornwood Automation made it."}]).reason == "DENY_UNPARSEABLE_SOURCE"
    assert assess_evidence(QUESTION, [{"id": "x", "text": VALID["text"] + " This is uncertain."}]).reason == "DENY_UNPARSEABLE_SOURCE"
    assert assess_evidence(QUESTION, [VALID, VALID]).reason == "DENY_DUPLICATE_SOURCE_ID"
    assert assess_evidence(QUESTION, [None]).reason == "DENY_UNTRUSTED_SOURCE_FORMAT"
    assert assess_evidence(QUESTION, [{"id": "x", "text": None}]).reason == "DENY_UNTRUSTED_SOURCE_FORMAT"



def test_postgeneration_structured_relation_and_exact_labels_not_syntax_only():
    accurate = "Thornwood Automation developed the Pulsar Guidance Node installed on the Arden Crawler. [S1]"
    verdict = assess_candidate(QUESTION, [VALID], accurate)
    assert verdict["development_match"]
    assert verdict["safe_to_publish"] is False
    assert verdict["human_semantic_verification"] == "NOT_PERFORMED"
    for text, expected in (
        ("Bluepeak Science developed the Pulsar Guidance Node installed on the Arden Crawler [S1].", "DENY_RELATION_OR_VALUE_MISMATCH"),
        ("Thornwood Automation developed the Gale Optical Sensor installed on the Arden Crawler [S1].", "DENY_RELATION_OR_VALUE_MISMATCH"),
        ("Thornwood Automation developed the Pulsar Guidance Node installed on the Arden Crawler [S99].", "DENY_UNSUPPORTED_CITATION_LABEL"),
        ("Thornwood Automation developed the Pulsar Guidance Node installed on the Arden Crawler.", "DENY_UNSUPPORTED_ANSWER_GRAMMAR"),
        ("The company was Thornwood Automation [S1].", "DENY_UNSUPPORTED_ANSWER_GRAMMAR"),
    ):
        res = assess_candidate(QUESTION, [VALID], text)
        assert not res["development_match"]
        assert not res["safe_to_publish"]
        assert res["reason"] == expected


def test_negative_cases_never_pass_postcheck_even_with_syntactically_valid_claims():
    claim = "Bluepeak Science developed the Pulsar Guidance Node installed on the Arden Crawler [S1]."
    for source in ([FOIL], [VALID, OTHER], []):
        out = assess_candidate(QUESTION, source, claim)
        assert not out["development_match"]
        assert out["reason"].startswith("DENIED_PREGEN:")
        assert not out["safe_to_publish"]


def test_frozen_synthetic_cohort_used_as_exposed_development_diagnostic_only():
    counts = {"allowed": 0, "denied": 0}
    by_class = {}
    for case in validate_protocol():
        decision = assess_evidence(case["question"], case["sources"])
        category = case["category"]  # Only tests know the authored label.
        by_class.setdefault(category, []).append(decision.allow_generation)
        counts["allowed" if decision.allow_generation else "denied"] += 1
    assert counts == {"allowed": 6, "denied": 18}
    assert by_class["answerable"] == [True] * 6
    assert all(v is False for group in ("irrelevant", "conflicting", "no_context")
               for v in by_class[group])


class UnreachableGenerator:
    name = "stub_no_model_call"

    def generate(self, *, system_prompt, user_prompt, max_new_tokens):
        raise AssertionError("Unsafe evidence must never invoke generator")


def test_optional_real_pipeline_callback_can_abstain_before_inference():
    docs = [Document("a", FOIL["text"], "irrelevant source")]
    retriever = FixedEvidenceRetriever(["a"])
    pipeline = RAGPipeline(
        documents=docs, retriever=retriever,
        context_builder=ContextBuilder(max_chars=3500, per_source_chars=1200),
        generator=UnreachableGenerator(),
        top_k=2,
        evidence_gate=make_research_evidence_gate({d.id: d for d in docs}),
    )
    pipeline.index()
    answer = pipeline.answer(QUESTION)
    assert answer.output_status == "abstained_evidence_gate"
    assert answer.abstained
    assert answer.timings_ms["generation"] == 0


def test_default_pipeline_no_gate_is_untouched_and_does_not_use_guard():
    # No changes are made to RAGPipeline. Only a research copy opts into the
    # existing evidence_gate callback. No implication for default publishing.
    from inspect import signature
    assert signature(RAGPipeline).parameters["evidence_gate"].default is None
