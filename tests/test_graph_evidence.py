import copy

import pytest

from raglab.core import Document
from raglab.graph import EvidenceEdge, EvidenceGraphRetriever, GraphNode
from raglab.observatory.fixture import create_demo_artifact, validate_observatory_artifact
from raglab.retrieval import BM25Retriever


def test_two_hop_path_preserves_original_sources():
    artifact = create_demo_artifact()
    trace = artifact["traces"][0]["trace"]
    assert trace["seed_entity_ids"] == ["rover"]
    assert [row["hop_count"] for row in trace["paths"]] == [1, 2]
    assert trace["paths"][1]["edge_ids"] == ["edge-uses", "edge-developed"]
    assert trace["paths"][1]["source_document_ids"] == ["doc-rover", "doc-navigation"]
    assert trace["ranked_document_ids"][:2] == ["doc-rover", "doc-navigation"]
    assert artifact["publication_status"] == "illustrative_fixture_not_benchmark"
    assert artifact["quantitative_benchmark_metrics"] is None
    assert all(item["answer"] is None for item in artifact["traces"])


def test_graph_is_deterministic_and_fingerprint_stable():
    assert create_demo_artifact() == create_demo_artifact()


def test_rejects_fabricated_evidence_quotes():
    graph = EvidenceGraphRetriever(BM25Retriever(), nodes=[GraphNode("a", "Alpha"), GraphNode("b", "Beta")],
        edges=[EvidenceEdge("e", "a", "related_to", "b", "d", "Never stated")])
    with pytest.raises(ValueError, match="quote"):
        graph.index([Document("d", "Alpha knows Beta")])


def test_rejects_missing_document_and_ambiguous_aliases():
    graph = EvidenceGraphRetriever(BM25Retriever(), nodes=[GraphNode("a", "Alpha"), GraphNode("b", "Alpha")], edges=[])
    with pytest.raises(ValueError, match="Ambiguous"):
        graph.index([Document("d", "Alpha")])
    graph = EvidenceGraphRetriever(BM25Retriever(), nodes=[GraphNode("a", "Alpha"), GraphNode("b", "Beta")],
        edges=[EvidenceEdge("e", "a", "r", "b", "missing", "source")])
    with pytest.raises(ValueError, match="missing document"):
        graph.index([Document("d", "source")])


def test_auditor_rejects_disconnected_paths_and_altered_sources():
    artifact = create_demo_artifact()
    bad = copy.deepcopy(artifact)
    bad["graph"]["edges"][0]["quote"] = "Uncited claim invented"
    with pytest.raises(ValueError, match="exact quoted"):
        validate_observatory_artifact(bad)
    bad = copy.deepcopy(artifact)
    bad["traces"][0]["trace"]["paths"][1]["edge_ids"][0] = "edge-sensor"
    with pytest.raises(ValueError, match="(disconnected|provenance mismatch)"):
        validate_observatory_artifact(bad)


def test_empty_seed_falls_back_without_claiming_graph_evidence():
    artifact = create_demo_artifact()
    assert artifact["traces"][0]["trace"]["semantic_support_verified"] is False
    graph = EvidenceGraphRetriever(BM25Retriever(), nodes=[GraphNode("x", "X"), GraphNode("y", "Y")],
        edges=[EvidenceEdge("e", "x", "related_to", "y", "a", "X connects to Y.")])
    graph.index([Document("a", "X connects to Y."), Document("b", "Something else")])
    ranked, trace = graph.retrieve_with_trace("unseen", 1)
    assert len(ranked) == 1 and trace["paths"] == [] and trace["seed_entity_ids"] == []
    with pytest.raises(ValueError, match="positive"):
        graph.retrieve("X", 0)
