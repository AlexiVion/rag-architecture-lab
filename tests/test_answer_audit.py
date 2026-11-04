from raglab.evaluation.answer_audit import audit_answer_artifact


def _artifact(answer: str, sources=None, abstained=False):
    return {
        "dataset": "toy",
        "query_id": "q",
        "result": {
            "question": "What happened?",
            "answer": answer,
            "abstained": abstained,
            "retrieval_name": "hybrid",
            "generator_name": "fake",
            "sources": sources if sources is not None else [
                {"label": "S1", "doc_id": "a", "title": "Relevant study"},
                {"label": "S2", "doc_id": "b", "title": "Other study"},
            ],
            "timings_ms": {"generation": 12.0, "retrieval": 1.0, "total": 13.0},
        },
    }


def test_uncited_answer_is_failure_not_execution_success():
    result = audit_answer_artifact(_artifact("Unsupported statement."))
    assert result["citation_status"] == "failed"
    assert result["semantic_support"] == "not_evaluated"
    assert result["citation_count"] == 0


def test_qrel_evidence_diagnostic_is_offline_only():
    result = audit_answer_artifact(
        _artifact("A claim [S1]."), relevant_doc_ids={"a", "c"}
    )
    assert result["citation_status"] == "passed"
    assert result["qrel_retrieval"]["recall_at_context_k"] == 0.5
    assert result["qrel_retrieval"]["relevant_sources_in_context"] == ["a"]
    assert result["answer_correctness"] == "not_evaluated"


def test_abstained_answer_does_not_require_fake_citation():
    result = audit_answer_artifact(_artifact("Not enough evidence.", abstained=True))
    assert result["citation_status"] == "not_applicable_abstained"


def test_invalid_citation_label_fails_quality_gate():
    result = audit_answer_artifact(_artifact("A claim [S99]."))
    assert result["citation_status"] == "failed"
    assert result["invalid_citation_labels"] == ["S99"]
