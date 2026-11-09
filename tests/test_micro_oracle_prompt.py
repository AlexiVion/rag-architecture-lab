from __future__ import annotations

import pytest

from raglab.core import Document
from raglab.micro.experiment import parse_dataset, run_micro_suite
from raglab.micro.oracle_diagnostics import gold_answer_window
from raglab.micro.role_prompts import (
    base_completion_prompt, instruction_chat_system,
    instruction_chat_user, question_and_evidence, RoleAdaptedQAGenerator,
)
from raglab.micro.squad_benchmark import GoldReference, NaturalQABenchmark
from raglab.micro.squad_metrics import evaluate_squad_traces


def test_gold_oracle_window_contains_answer_with_exact_original_offsets():
    text = "An unrelated introduction. Mars has two moons, Phobos and Deimos. Next sentence."
    doc = Document("d1", text)
    outcome = gold_answer_window(
        doc, ("Phobos and Deimos",), max_tokens=26
    )
    assert outcome.status == "gold_answer_centered_privileged_source"
    assert outcome.privileged_annotation_used is True
    assert outcome.answer_visible is True
    assert outcome.pack.used_tokens <= 26
    assert len(outcome.pack.spans) == 1
    span = outcome.pack.spans[0]
    assert span.doc_id == "d1"
    assert text[span.start:span.end] == span.quote
    assert "Phobos and Deimos" in span.quote
    assert "doc_id=" not in outcome.pack.text
    assert "chars=" not in outcome.pack.text


def test_oracle_gold_too_long_is_excluded_without_truncating():
    doc = Document("d", "An extra long reference answer must stay intact.")
    outcome = gold_answer_window(
        doc, ("extra long reference answer",), max_tokens=2
    )
    assert outcome.status == "gold_too_long_for_token_budget"
    assert outcome.pack.spans == ()
    assert outcome.answer_visible is False


def test_oracle_negative_exposes_only_original_paragraph():
    doc = Document("d", "This paragraph describes a garden but never names its owner.")
    outcome = gold_answer_window(doc, (), max_tokens=32)
    assert outcome.status == "negative_original_paragraph_not_open_corpus_proof"
    assert outcome.pack.spans
    assert not outcome.answer_visible
    assert outcome.pack.spans[0].quote in doc.text


def test_oracle_refuses_unsupported_annotation():
    doc = Document("d", "Only a river is mentioned.")
    outcome = gold_answer_window(doc, ("different answer",), max_tokens=128)
    assert outcome.status == "gold_not_found_in_source"
    assert not outcome.pack.spans


def _small():
    return parse_dataset({
        "schema_version": 1,
        "dataset_id": "oracle-unit-synthetic",
        "fixture_only": True,
        "documents": [
            {"id": "d", "text": "The star is named Caldor. No planets are mentioned."},
            {"id": "e", "text": "A forest covers the hill."},
        ],
        "cases": [
            {
                "id": "answer", "question": "What is the star named?",
                "group_id": "group-star", "split": "dev", "oracle_doc_ids": ["d"],
            },
            {
                "id": "negative", "question": "What is the planet named?",
                "group_id": "group-star", "split": "dev", "oracle_doc_ids": ["d"],
            },
        ],
    })


def test_oracle_run_fails_closed_without_gold_annotations():
    with pytest.raises(ValueError, match="explicit complete privileged"):
        run_micro_suite(
            _small(), model_id="pythia-14m", modes=("oracle_window",)
        )


def test_oracle_scoring_does_not_credit_gold_to_retrieval():
    data = _small()
    annotation = {"answer": ("Caldor",), "negative": ()}
    trial = run_micro_suite(
        data,
        model_id="pythia-14m",
        modes=("spans_compact", "oracle", "oracle_window"),
        max_context_tokens=40,
        gold_answers_by_case=annotation,
    )
    oracle_rows = [row for row in trial["cases"] if row["mode"] == "oracle_window"]
    assert len(oracle_rows) == 2
    assert all(row["oracle_used"] for row in oracle_rows)
    assert next(x for x in oracle_rows if x["case_id"] == "answer")[
        "oracle_gold_literal_visible"
    ] is True
    assert next(x for x in oracle_rows if x["case_id"] == "negative")[
        "oracle_gold_literal_visible"
    ] is False
    assert all(
        row["oracle_window_status"] is None and not row["oracle_used"]
        for row in trial["cases"] if row["mode"] == "spans_compact"
    )
    refs = {
        "answer": GoldReference("answer", ("Caldor",), True, "d", "test"),
        "negative": GoldReference("negative", (), False, "d", "test"),
    }
    benchmark = NaturalQABenchmark(
        dataset=data, references=refs, source_sha256="unit",
        source_name="unit-only", source_license="unit-only",
        sampling_version="unit-only",
    )
    evaluation = evaluate_squad_traces(benchmark, trial)
    assert evaluation["by_mode"]["oracle_window"]["gold_doc_recall_at_k"] is None
    assert evaluation["by_mode"]["oracle"]["gold_doc_recall_at_k"] is None
    assert evaluation["by_mode"]["spans_compact"]["gold_doc_recall_at_k"] == 1.0


def test_task_prompt_formatting_is_static_without_squad_examples():
    s = (
        "Question:\nWho discovered it?\n\n"
        "Evidence:\n[S1]\nA stone is red.\n\n"
        "If there is insufficient evidence, abstain. Cite exact evidence IDs. "
        "Never claim that a citation alone proves the answer."
    )
    question, evidence = question_and_evidence(s)
    assert question == "Who discovered it?"
    assert evidence == "[S1]\nA stone is red."
    base = base_completion_prompt(question, evidence)
    assert base.endswith("Question: Who discovered it?\nAnswer:")
    assert base.count("INSUFFICIENT_EVIDENCE") == 2
    assert "SYSTEM:" not in base and "USER:" not in base
    assert "SQuAD" not in base
    assert "The silver comet" in base
    assert "shortest" in instruction_chat_system()
    assert instruction_chat_user(question, evidence).endswith(
        "Question:\nWho discovered it?\n\nAnswer:"
    )
    with pytest.raises(ValueError):
        question_and_evidence("unstructured prompt")


def test_generator_constructor_rejects_unknown_role():
    class LocalStub:
        name = "stub"
    with pytest.raises(ValueError, match="model_role"):
        RoleAdaptedQAGenerator(LocalStub(), model_role="unknown")
