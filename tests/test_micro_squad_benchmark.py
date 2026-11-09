from __future__ import annotations

import hashlib
import json

import pytest

from raglab.micro.experiment import run_micro_suite
from raglab.micro.squad_benchmark import _split, load_official_squad_dev
from raglab.micro.squad_metrics import (
    evaluate_squad_traces, is_abstention, normalize_answer, score_prediction,
)


def _make_official_dev(tmp_path):
    articles = []
    for n in range(40):
        title = f"Article {n}"
        if _split(title) != "dev":
            continue
        context = (
            f"The indicator in region {n} is blue. "
            f"This paragraph contains scientific statements in natural language. "
            f"A short second sentence describes another source feature."
        )
        articles.append(
            {
                "title": title,
                "paragraphs": [
                    {
                        "context": context,
                        "qas": [
                            {
                                "id": f"answer-{n}",
                                "question": f"What color is the indicator in region {n}?",
                                "answers": [
                                    {"text": "blue", "answer_start": context.index("blue")}
                                ],
                                "is_impossible": False,
                            },
                            {
                                "id": f"none-{n}",
                                "question": f"Who discovered the indicator in region {n}?",
                                "answers": [],
                                "is_impossible": True,
                            },
                        ],
                    }
                ],
            }
        )
    assert len(articles) >= 4
    payload = {"version": "v2.0", "data": articles}
    path = tmp_path / "real-schema-synthetic-unit-only.json"
    raw = json.dumps(payload).encode("utf-8")
    path.write_bytes(raw)
    return path, hashlib.sha256(raw).hexdigest()


def test_natural_schema_loader_deterministic_and_balanced_by_article(tmp_path):
    path, sha = _make_official_dev(tmp_path)
    a = load_official_squad_dev(path, expected_sha256=sha, max_cases=8, distractors=2)
    b = load_official_squad_dev(path, expected_sha256=sha, max_cases=8, distractors=2)
    assert a.dataset.fingerprint == b.dataset.fingerprint
    assert len(a.dataset.cases) == 8
    assert a.dataset.fixture_only is False
    assert a.manifest()["distinct_articles"] == 4
    assert a.manifest()["answerable"] == 4
    assert a.manifest()["unanswerable"] == 4
    assert all(case.split == "dev" for case in a.dataset.cases)
    assert len(a.references) == 8
    for case in a.dataset.cases:
        gold = a.references[case.case_id]
        assert gold.gold_doc_id in {doc.id for doc in a.dataset.documents}
        assert gold.official_title == case.group_id


def test_reject_tampered_data_and_forbidden_splits(tmp_path):
    path, sha = _make_official_dev(tmp_path)
    with pytest.raises(ValueError, match="SHA256 mismatch"):
        load_official_squad_dev(path)
    with pytest.raises(ValueError, match="DEV only"):
        load_official_squad_dev(path, expected_sha256=sha, split="holdout")
    with pytest.raises(ValueError, match="positive even"):
        load_official_squad_dev(path, expected_sha256=sha, max_cases=3)


def test_short_answer_metrics_do_not_treat_citations_as_entailment():
    yes = score_prediction("The blue [S1]", ["blue"], generation_status="draft_unverified")
    assert yes["reference_em"] == 0.0  # extra words cannot be silently ignored
    exact = score_prediction("Blue. [S3]", ["blue"], generation_status="draft_unverified")
    assert exact["reference_em"] == 1.0
    assert exact["reference_f1"] == 1.0
    no = score_prediction(
        "INSUFFICIENT_EVIDENCE",
        [],
        generation_status="draft_unverified",
    )
    assert no["reference_em"] == 1.0
    assert no["abstained"] is True
    assert is_abstention("I may not know") is False
    assert normalize_answer("The blue [S99]!") == "blue"


def test_evaluation_never_claims_semantic_factuality(tmp_path):
    path, sha = _make_official_dev(tmp_path)
    benchmark = load_official_squad_dev(path, expected_sha256=sha, max_cases=8, distractors=3)

    class FakeGenerator:
        name = "FAKE_NOT_A_MODEL"

        def generate(self, *, system_prompt, user_prompt, max_new_tokens):
            return "blue [S1]"

    trace = run_micro_suite(
        benchmark.dataset,
        model_id="pythia-14m",
        generator=FakeGenerator(),
        modes=("no_retrieval", "naive", "spans"),
        max_context_tokens=128,
    )
    scored = evaluate_squad_traces(benchmark, trace)
    assert scored["status"] == "PUBLIC_DEV_REFERENCE_METRICS_NOT_SEMANTIC_VALIDATION"
    assert len(scored["cases"]) == 24
    assert set(scored["by_mode"]) == {"no_retrieval", "naive", "spans"}
    assert scored["by_mode"]["spans"]["n_answerable_scored"] == 4
    assert scored["by_mode"]["spans"]["n_unanswerable_scored"] == 4
    assert all(x["reference_em"] in (0.0, 1.0) for x in scored["cases"])
    assert all("source_supported" not in row for row in scored["cases"])


def test_scoring_rejects_unexpected_dataset_fingerprint(tmp_path):
    path, sha = _make_official_dev(tmp_path)
    benchmark = load_official_squad_dev(path, expected_sha256=sha, max_cases=8)
    trace = run_micro_suite(benchmark.dataset, model_id="pythia-14m")
    trace["dataset"]["sha256"] = "TAMPERED"
    with pytest.raises(ValueError, match="fingerprints differ"):
        evaluate_squad_traces(benchmark, trace)


def test_placeholder_dry_run_stays_unscored(tmp_path):
    path, sha = _make_official_dev(tmp_path)
    benchmark = load_official_squad_dev(path, expected_sha256=sha, max_cases=8)
    trace = run_micro_suite(benchmark.dataset, model_id="pythia-14m")
    result = evaluate_squad_traces(benchmark, trace)
    assert result["by_mode"]["naive"]["reference_em"] is None
    assert result["by_mode"]["no_retrieval"]["reference_f1"] is None
