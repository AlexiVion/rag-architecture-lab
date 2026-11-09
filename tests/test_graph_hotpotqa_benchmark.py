from __future__ import annotations

import copy
import hashlib
import json

import pytest

from raglab.graph import EvidenceGraphRetriever
from raglab.graph.hotpotqa_benchmark import (
    HOTPOT_SHA256,
    benchmark_bridge_dev,
    cached_hotpotqa,
    case_documents,
    derive_title_link_graph,
    load_bridge_dev_rows,
    recall_at_k,
)
from raglab.retrieval import BM25Retriever


def sample_record(key="q1", type_="bridge"):
    return {
        "_id": key,
        "type": type_,
        "level": "easy",
        "question": "Where was Project Alpha created before Ada Scientist moved?",
        "answer": "Beta Institution",
        "context": [
            ["Project Alpha", ["Project Alpha was created at Beta Institution."]],
            ["Beta Institution", ["Ada Scientist joined Beta Institution in 2002."]],
            ["Ada Scientist", ["Ada Scientist helped build Project Alpha."]],
            ["Unrelated page", ["This article covers the weather."]],
        ],
        "supporting_facts": [["Project Alpha", 0], ["Beta Institution", 0]],
    }


def test_bridge_selection_deterministic_and_scoped(tmp_path):
    rows = [
        sample_record("q2"),
        sample_record("q1"),
        sample_record("ignored", type_="comparison"),
    ]
    path = tmp_path / "dev.json"
    path.write_text(json.dumps(rows), encoding="utf-8")
    selected = load_bridge_dev_rows(path, seed=17, count=2)
    assert {item["_id"] for item in selected} == {"q1", "q2"}
    assert [x["_id"] for x in selected] == [
        x["_id"] for x in load_bridge_dev_rows(path, seed=17, count=2)
    ]
    with pytest.raises(ValueError, match="Only 2"):
        load_bridge_dev_rows(path, count=3)


def test_graph_links_derive_from_text_not_supporting_facts():
    row = sample_record()
    docs, titles, gold = case_documents(row)
    nodes, edges = derive_title_link_graph(docs)
    assert len(nodes) == len(docs)
    assert edges
    assert any(
        edge.source == titles["Project Alpha"]
        and edge.target == titles["Beta Institution"]
        and edge.quote in docs[0].text
        for edge in edges
    )
    altered = copy.deepcopy(row)
    altered["supporting_facts"] = [["Ada Scientist", 0], ["Unrelated page", 0]]
    docs2, _, gold2 = case_documents(altered)
    nodes2, edges2 = derive_title_link_graph(docs2)
    assert (nodes, edges) == (nodes2, edges2)
    assert gold != gold2
    graph = EvidenceGraphRetriever(BM25Retriever(), nodes=nodes, edges=edges)
    graph.index(docs)
    ranked, trace = graph.retrieve_with_trace(row["question"], 3)
    assert ranked
    assert trace["paths"]
    assert all(edge.document_id in {doc.id for doc in docs} for edge in edges)


def test_retrieval_metrics_are_paired_and_truthfully_described():
    report = benchmark_bridge_dev([sample_record()], seed=17)
    assert report["sample_count"] == 1
    assert report["graph_built_without_gold_labels"]
    assert report["dataset"] == "hotpotqa/distractor/dev_v1"
    assert report["retrieval_scope"].startswith("per-question")
    assert "not answer generation" in report["relevance_target"]
    for metric in ("recall@1", "recall@3", "recall@5"):
        scores = report["metrics"][metric]
        assert 0 <= scores["bm25"] <= 1
        assert 0 <= scores["graph_plus_bm25"] <= 1
        assert scores["wins"] + scores["losses"] + scores["ties"] == 1
        assert len(scores["paired_bootstrap_95ci"]) == 2
    assert report["metrics"]["recall@5"]["bm25"] == pytest.approx(1.0)
    assert report["metrics"]["recall@5"]["graph_plus_bm25"] == pytest.approx(1.0)


def test_no_answer_quality_is_measured():
    report = benchmark_bridge_dev([sample_record()], seed=17)
    text = " ".join(report["limitations"])
    assert "do not measure answer correctness" in text.lower()
    assert "not full wikipedia" in report["retrieval_scope"].lower()


def test_recall_math_excludes_missing_document():
    assert recall_at_k(["a", "c"], {"a", "b"}, 1) == pytest.approx(0.5)
    assert recall_at_k(["a", "c"], {"a", "b"}, 2) == pytest.approx(0.5)
    with pytest.raises(ValueError, match="Nonempty"):
        recall_at_k(["a"], set(), 1)


def test_checksum_mismatch_never_silently_overwrites_cache(tmp_path):
    path = tmp_path / "hotpot.json"
    path.write_text("not official source", encoding="utf-8")
    assert hashlib.sha256(path.read_bytes()).hexdigest() != HOTPOT_SHA256
    with pytest.raises(ValueError, match="checksum mismatch"):
        cached_hotpotqa(path)
    assert path.read_text(encoding="utf-8") == "not official source"


def test_absent_gold_context_is_excluded_not_reclassified(tmp_path):
    record = sample_record()
    record["supporting_facts"] = [["A Missing Article", 0], ["Project Alpha", 0]]
    path = tmp_path / "hotpot.json"
    path.write_text(json.dumps([record]), encoding="utf-8")
    with pytest.raises(ValueError, match="Only 0"):
        load_bridge_dev_rows(path, count=1)
