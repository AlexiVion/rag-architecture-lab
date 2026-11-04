"""Generate a truthful, offline provenance demo without downloads or LLMs."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from raglab.core import Document
from raglab.core.fingerprint import fingerprint_documents
from raglab.graph import EvidenceEdge, EvidenceGraphRetriever, GraphNode
from raglab.retrieval import BM25Retriever

DOCUMENTS = (
    Document("doc-rover", "The Aster Rover uses the Orion Navigation System.", "Mission log"),
    Document("doc-navigation", "The Orion Navigation System was developed by Meridian Robotics.", "Engineering notes"),
    Document("doc-solar", "The Solis Probe has a thermal sensor made by Helios Instruments.", "Independent mission"),
)
NODES = (
    GraphNode("rover", "Aster Rover", ("Aster",)),
    GraphNode("navigation", "Orion Navigation System", ("Orion",)),
    GraphNode("manufacturer", "Meridian Robotics"),
    GraphNode("probe", "Solis Probe"),
    GraphNode("sensor", "thermal sensor"),
    GraphNode("instrument", "Helios Instruments"),
)
EDGES = (
    EvidenceEdge("edge-uses", "rover", "uses", "navigation", "doc-rover",
                 "The Aster Rover uses the Orion Navigation System."),
    EvidenceEdge("edge-developed", "navigation", "developed_by", "manufacturer",
                 "doc-navigation", "The Orion Navigation System was developed by Meridian Robotics."),
    EvidenceEdge("edge-sensor", "probe", "carries", "sensor", "doc-solar",
                 "The Solis Probe has a thermal sensor made by Helios Instruments."),
    EvidenceEdge("edge-sensor-maker", "sensor", "made_by", "instrument", "doc-solar",
                 "The Solis Probe has a thermal sensor made by Helios Instruments."),
)
QUERIES = (
    "Which organization developed the navigation system used by the Aster Rover?",
    "Which navigation system does the Aster Rover use?",
    "Who made the thermal sensor on the Solis Probe?",
)


def create_demo_artifact() -> dict:
    graph = EvidenceGraphRetriever(BM25Retriever(), nodes=NODES, edges=EDGES)
    graph.index(DOCUMENTS)
    traces = []
    for index, question in enumerate(QUERIES, start=1):
        ranked, trace = graph.retrieve_with_trace(question, 3)
        traces.append({
            "id": f"fixture-query-{index}",
            "question": question,
            "ranked_sources": [
                {"doc_id": item.doc_id, "rank": item.rank, "score": item.score}
                for item in ranked
            ],
            "trace": trace,
            "answer": None,
            "generation_status": "not_run",
            "answer_truth_status": "not_evaluated",
        })
    data = {
        "schema_version": 1,
        "kind": "graph_evidence_fixture",
        "publication_status": "illustrative_fixture_not_benchmark",
        "dataset": "offline-curated-aster-demo-v1",
        "corpus_sha256": fingerprint_documents(sorted(DOCUMENTS, key=lambda d: d.id)),
        "extraction_method": "manually_curated_exact_quotes",
        "model_name": None,
        "quantitative_benchmark_metrics": None,
        "graph": graph.graph_export(),
        "traces": traces,
        "license": "MIT demo fiction - generated for this repository",
    }
    validate_observatory_artifact(data)
    return data


def validate_observatory_artifact(payload: dict) -> None:
    """Fail-closed checks for graph/source integrity in public fixtures."""
    if payload.get("schema_version") != 1 or payload.get("kind") != "graph_evidence_fixture":
        raise ValueError("Unsupported observatory artifact schema")
    if payload.get("publication_status") != "illustrative_fixture_not_benchmark":
        raise ValueError("Fixture must not be represented as a measured benchmark")
    graph = payload.get("graph")
    if not isinstance(graph, dict):
        raise ValueError("Missing graph")
    documents = graph.get("documents", [])
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])
    doc_lookup = {doc["id"]: doc for doc in documents}
    node_ids = {node["id"] for node in nodes}
    edge_lookup = {edge["id"]: edge for edge in edges}
    if (not documents or not nodes or not edges
        or len(doc_lookup) != len(documents) or len(node_ids) != len(nodes)
        or len(edge_lookup) != len(edges)):
        raise ValueError("Graph references must have unique nonempty collections")
    actual_docs = [Document(d["id"], d["text"], d["title"]) for d in documents]
    if fingerprint_documents(actual_docs) != payload.get("corpus_sha256"):
        raise ValueError("Corpus fingerprint mismatch")
    for edge in edges:
        if edge["source"] not in node_ids or edge["target"] not in node_ids:
            raise ValueError("Graph edge has an unknown endpoint")
        doc = doc_lookup.get(edge["document_id"])
        if not doc or edge["quote"] not in (doc["title"] + "\n" + doc["text"]):
            raise ValueError("Graph relation lacks exact quoted source evidence")
    traces = payload.get("traces", [])
    if not isinstance(traces, list) or not traces:
        raise ValueError("Fixture must contain visible trace examples")
    for example in traces:
        trace = example["trace"]
        if example.get("generation_status") != "not_run" or example.get("answer") is not None:
            raise ValueError("Fixture may not present fabricated generated answers")
        if trace["question"] != example["question"]:
            raise ValueError("Trace/question mismatch")
        for path in trace.get("paths", []):
            if len(path["edge_ids"]) != path["hop_count"]:
                raise ValueError("Graph path hop length mismatch")
            if any(eid not in edge_lookup for eid in path["edge_ids"]):
                raise ValueError("Graph path has unknown relation")
            if any(nid not in node_ids for nid in path["node_ids"]):
                raise ValueError("Graph path has unknown node")
            if len(path["node_ids"]) != len(path["edge_ids"]) + 1:
                raise ValueError("Graph path is disconnected by node count")
            expected_sources = list(dict.fromkeys(
                edge["document_id"] for edge in edges
                if edge["id"] in path["edge_ids"]
            ))
            if path.get("source_document_ids") != expected_sources:
                raise ValueError("Graph path source provenance mismatch")
            for index, eid in enumerate(path["edge_ids"]):
                edge = edge_lookup[eid]
                pair = {path["node_ids"][index], path["node_ids"][index + 1]}
                if pair != {edge["source"], edge["target"]}:
                    raise ValueError("Graph path references a disconnected edge")
        if trace.get("ranked_document_ids") != [r["doc_id"] for r in example["ranked_sources"]]:
            raise ValueError("Ranked source list does not match trace")
        for result in example["ranked_sources"]:
            if result["doc_id"] not in doc_lookup:
                raise ValueError("Retrieved source ID missing from artifact")


def main() -> None:
    parser = argparse.ArgumentParser(description="Export verified offline GraphRAG fixture")
    parser.add_argument("--output", default="apps/explorer/data/demo.json")
    args = parser.parse_args()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    data = create_demo_artifact()
    serialized = json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    output.write_text(serialized, encoding="utf-8")
    sha = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
    print(f"GRF00_FIXTURE_EXPORTED={output}")
    print(f"GRF00_FIXTURE_SHA256={sha}")
    print("Fixture contains only curated evidence; no model or benchmark claims.")


if __name__ == "__main__":
    main()
