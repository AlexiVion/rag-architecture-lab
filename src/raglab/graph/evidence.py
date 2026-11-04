"""Deterministic, provenance-checked graph retrieval baseline.

This is a graph traversal implementation over *supplied, cited relations*, not
an automated entity extractor or a full community-summary GraphRAG system.
"""
from __future__ import annotations

import re
from collections import defaultdict, deque
from collections.abc import Sequence
from dataclasses import asdict, dataclass

from raglab.core import Document, SearchResult
from raglab.retrieval.base import Retriever


@dataclass(frozen=True, slots=True)
class GraphNode:
    id: str
    label: str
    aliases: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class EvidenceEdge:
    id: str
    source: str
    relation: str
    target: str
    document_id: str
    quote: str


class EvidenceGraphRetriever:
    """Graph-first retriever with lexical fallback and inspectable paths.

    All edges must point to an existing document and an exact quoted passage.
    A query may seed one or more nodes by alias; traversal is bounded to two
    hops and returns original document IDs. Indexing is replace-not-append.
    """

    name = "graph-evidence"

    def __init__(
        self,
        text_retriever: Retriever,
        *,
        nodes: Sequence[GraphNode],
        edges: Sequence[EvidenceEdge],
        max_hops: int = 2,
    ) -> None:
        if max_hops not in (1, 2):
            raise ValueError("Graph traversal must be bounded to one or two hops")
        self.text_retriever = text_retriever
        self.nodes = tuple(nodes)
        self.edges = tuple(edges)
        self.max_hops = max_hops
        self._documents: dict[str, Document] = {}
        self._adjacency: dict[str, list[EvidenceEdge]] = {}
        self._indexed = False

    def index(self, documents: Sequence[Document]) -> None:
        docs = list(documents)
        by_doc = {doc.id: doc for doc in docs}
        by_node = {node.id: node for node in self.nodes}
        if not docs or len(by_doc) != len(docs):
            raise ValueError("Graph needs nonempty documents with unique IDs")
        if not self.nodes or len(by_node) != len(self.nodes):
            raise ValueError("Graph needs unique, nonempty entity nodes")
        if any(not n.id.strip() or not n.label.strip() for n in self.nodes):
            raise ValueError("Graph node ID/label cannot be empty")
        seen_aliases: dict[str, str] = {}
        for node in self.nodes:
            for alias in (node.label, *node.aliases):
                key = alias.strip().casefold()
                if not key:
                    raise ValueError("Graph aliases cannot be empty")
                if key in seen_aliases and seen_aliases[key] != node.id:
                    raise ValueError("Ambiguous graph aliases across entity IDs")
                seen_aliases[key] = node.id
        adjacency: dict[str, list[EvidenceEdge]] = defaultdict(list)
        edge_ids: set[str] = set()
        for edge in self.edges:
            if not edge.id.strip() or edge.id in edge_ids:
                raise ValueError("Graph evidence edge IDs must be unique/nonempty")
            edge_ids.add(edge.id)
            if edge.source not in by_node or edge.target not in by_node:
                raise ValueError(f"Graph edge {edge.id} references an unknown entity")
            if edge.document_id not in by_doc:
                raise ValueError(f"Graph edge {edge.id} references a missing document")
            if not edge.relation.strip() or not edge.quote.strip():
                raise ValueError(f"Graph edge {edge.id} lacks relation or quote")
            if edge.quote not in by_doc[edge.document_id].searchable_text:
                raise ValueError(f"Graph edge {edge.id} quote is not in source document")
            adjacency[edge.source].append(edge)
            if edge.target != edge.source:
                adjacency[edge.target].append(edge)
        for edges in adjacency.values():
            edges.sort(key=lambda e: e.id)
        # Validate *everything* before mutating the underlying retriever.
        self.text_retriever.index(docs)
        self._documents = by_doc
        self._adjacency = dict(adjacency)
        self._indexed = True

    def _seeds(self, query: str) -> list[str]:
        seeds = []
        for node in self.nodes:
            for name in (node.label, *node.aliases):
                if re.search(r"(?<!\w)" + re.escape(name) + r"(?!\w)", query, re.IGNORECASE):
                    seeds.append(node.id)
                    break
        return sorted(seeds)

    def retrieve_with_trace(self, query: str, k: int) -> tuple[list[SearchResult], dict]:
        if not self._indexed:
            raise RuntimeError("Graph must be indexed before retrieval")
        if not query.strip() or k <= 0:
            raise ValueError("Question and k must be nonempty/positive")
        seeds = self._seeds(query)
        queue = deque((seed, (seed,), ()) for seed in seeds)
        candidates: dict[str, tuple[float, int, tuple[str, ...]]] = {}
        paths: list[dict] = []
        expanded: set[tuple[str, tuple[str, ...]]] = set()
        while queue:
            node_id, path_nodes, path_edges = queue.popleft()
            if len(path_edges) >= self.max_hops:
                continue
            for edge in self._adjacency.get(node_id, ()):
                target = edge.target if node_id == edge.source else edge.source
                if target in path_nodes or edge.id in path_edges:
                    continue
                next_nodes = (*path_nodes, target)
                next_edges = (*path_edges, edge.id)
                key = (target, next_edges)
                if key in expanded:
                    continue
                expanded.add(key)
                depth = len(next_edges)
                paths.append({
                    "node_ids": list(next_nodes),
                    "edge_ids": list(next_edges),
                    "hop_count": depth,
                    "source_document_ids": list(dict.fromkeys(
                        e.document_id for e in self.edges if e.id in next_edges
                    )),
                })
                # The quote for the newly traversed edge is first-class evidence.
                # Prioritize shorter paths; never create artificial source IDs.
                score = 1.0 / depth
                prior = candidates.get(edge.document_id)
                if prior is None or score > prior[0]:
                    candidates[edge.document_id] = (score, depth, next_edges)
                queue.append((target, next_nodes, next_edges))
        ordered = sorted(candidates.items(), key=lambda item: (-item[1][0], item[0]))
        ranked_ids = [doc_id for doc_id, _ in ordered]
        text_results = self.text_retriever.retrieve(query, max(k, 1))
        score_by_id = {doc_id: score for doc_id, (score, _, _) in ordered}
        for result in text_results:
            if result.doc_id not in self._documents:
                raise ValueError("Lexical fallback returned an unknown source ID")
            if result.doc_id not in ranked_ids:
                ranked_ids.append(result.doc_id)
                # Negative scores clearly separate fallback from graph evidence.
                score_by_id[result.doc_id] = -float(result.rank)
        final = [
            SearchResult(doc_id=doc_id, score=score_by_id[doc_id], rank=rank)
            for rank, doc_id in enumerate(ranked_ids[:k], start=1)
        ]
        return final, {
            "schema_version": 1,
            "method": "bounded_provenance_graph_then_lexical_fallback",
            "question": query,
            "seed_entity_ids": seeds,
            "max_hops": self.max_hops,
            "paths": paths,
            "ranked_document_ids": [row.doc_id for row in final],
            "graph_hit_document_ids": sorted(candidates),
            "semantic_support_verified": False,
            "limitations": "Curated source-quoted edges; no learned extraction or verified answer.",
        }

    def retrieve(self, query: str, k: int) -> list[SearchResult]:
        ranked, _ = self.retrieve_with_trace(query, k)
        return ranked

    def graph_export(self) -> dict:
        if not self._indexed:
            raise RuntimeError("Graph must be indexed before export")
        return {
            "nodes": [asdict(node) for node in self.nodes],
            "edges": [asdict(edge) for edge in self.edges],
            "documents": [
                {"id": d.id, "title": d.title, "text": d.text}
                for d in sorted(self._documents.values(), key=lambda doc: doc.id)
            ],
        }
