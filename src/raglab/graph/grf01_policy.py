"""GRF-01 frozen policy: source-quoted graph as a small RRF complement.

Does not access HotpotQA qrels, answers, score files or the reserved evaluation
queries. This implementation is tested with synthetic sources before the
predeclared DEV cohort is evaluated.

This is NOT a pretrained knowledge-graph extractor or verified semantic judge.
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from raglab.core import Document, SearchResult
from raglab.fusion import reciprocal_rank_fusion
from raglab.graph.evidence import EvidenceGraphRetriever, EvidenceEdge, GraphNode
from raglab.graph.grf01_cohort import (
    COHORT_SCHEMA,
    HOTPOT_SHA256,
    PREVIOUS_STUDY_SHA256,
)
from raglab.graph.hotpotqa_benchmark import derive_title_link_graph

# Hugging Face model API revision, verified on 2026-11-04.
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_REVISION = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
EMBEDDING_LICENSE = "apache-2.0"
# Do not revise these on the 60 reserved DEV questions.
RRF_CONSTANT = 60
GRAPH_BONUS_WEIGHT = 0.10
MAX_HOPS = 2
CANDIDATE_K = 10
EXPECTED_COHORT_SHA256 = "a560b1cbabe1ce6b4413f0f6f59759cd08e69ce49c5391e05b7c8767f81bd13f"

POLICY = {
    "policy_id": "GRF01-GRAPH-HYBRID-v1-LOCKED",
    "experiment_id": "GRF01-HOTPOTQA-DEV-01",
    "dataset": "hotpotqa/distractor/dev_v1",
    "dataset_sha256": HOTPOT_SHA256,
    "model_id": EMBEDDING_MODEL,
    "model_revision": EMBEDDING_REVISION,
    "model_license": EMBEDDING_LICENSE,
    "device": "cpu",
    "dense_batch_size": 8,
    "candidate_k": CANDIDATE_K,
    "rrf_constant": RRF_CONSTANT,
    "graph_source": "unsupervised_exact_title_mentions",
    "graph_max_hops": MAX_HOPS,
    "graph_bonus_rule": "max_existing_RRF_score_plus_weight_over_rrf_constant_plus_min_evidence_hops",
    "graph_bonus_weight": GRAPH_BONUS_WEIGHT,
    "require_literal_relation_quotes": True,
    "no_graph_path_rule": "return_bitwise_identical_Hybrid_RRF_ranking",
    "same_sparse_and_dense_lists": True,
    "gold_labels_available_to_ranker": False,
    "previous_dev_cohort_excluded": True,
    "allow_test_tuning": False,
    "primary_metric": "paired_delta_supporting_document_recall_at_5",
}


def policy_fingerprint() -> str:
    return hashlib.sha256(
        json.dumps(POLICY, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


class PinnedMiniLMEmbeddings:
    """Optional local CPU encoder, with immutable revision and no paid API."""

    name = EMBEDDING_MODEL + "@" + EMBEDDING_REVISION

    def __init__(self) -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise RuntimeError('Install local model extras: pip install -e ".[benchmark]"') from exc
        self._model = SentenceTransformer(
            EMBEDDING_MODEL,
            revision=EMBEDDING_REVISION,
            device="cpu",
            trust_remote_code=False,
        )

    def encode(self, texts: Sequence[str]) -> np.ndarray:
        return np.asarray(
            self._model.encode(
                list(texts),
                batch_size=8,
                convert_to_numpy=True,
                normalize_embeddings=False,
                show_progress_bar=False,
            ),
            dtype=np.float32,
        )


class _ExistingRanking:
    """Never load/retrieve from a model twice to compute graph traces."""

    name = "frozen_hybrid_results"

    def __init__(self, ranking: list[SearchResult]) -> None:
        self._ranking = ranking

    def index(self, documents: Sequence[Document]) -> None:
        return None

    def retrieve(self, query: str, k: int) -> list[SearchResult]:
        return self._ranking[:k]


@dataclass(frozen=True)
class GraphHybridComparison:
    hybrid: list[SearchResult]
    graph_hybrid: list[SearchResult]
    trace: dict[str, Any]


def _validate_full_ranking(
    results: Sequence[SearchResult], document_ids: set[str], name: str
) -> None:
    if len(results) != len(document_ids):
        raise ValueError(name + " must rank ALL identical candidate documents")
    if [r.rank for r in results] != list(range(1, len(results) + 1)):
        raise ValueError(name + " ranks must be unique consecutive integers")
    ids = [r.doc_id for r in results]
    if set(ids) != document_ids or len(set(ids)) != len(ids):
        raise ValueError(name + " returned missing, duplicated or foreign source IDs")


def paired_rankings(
    query: str,
    documents: Sequence[Document],
    dense: Sequence[SearchResult],
    sparse: Sequence[SearchResult],
    *,
    k: int = 5,
    nodes: Sequence[GraphNode] | None = None,
    edges: Sequence[EvidenceEdge] | None = None,
) -> GraphHybridComparison:
    """Use the EXACT SAME sparse/dense result lists for both architectures.

    Gold labels are deliberately absent from this signature. Relationship
    quotes are verified against original Document contents during indexing.
    """
    docs = list(documents)
    ids = {d.id for d in docs}
    if not docs or len(ids) != len(docs) or any(not did for did in ids):
        raise ValueError("Candidates must be nonempty documents with unique IDs")
    if not query.strip() or k < 1 or k > len(docs):
        raise ValueError("Invalid nonempty question or top-k")
    _validate_full_ranking(dense, ids, "Dense")
    _validate_full_ranking(sparse, ids, "Sparse")
    # Canonical baseline matches the project HybridRetriever's fusion order.
    complete = reciprocal_rank_fusion(
        [list(dense), list(sparse)], k=len(docs), rrf_constant=RRF_CONSTANT
    )
    baseline = complete[:k]
    if nodes is None and edges is None:
        nodes, edges = derive_title_link_graph(docs)
    elif nodes is None or edges is None:
        raise ValueError("Nodes and edges must be supplied together")
    graph = EvidenceGraphRetriever(
        _ExistingRanking(complete), nodes=nodes, edges=edges, max_hops=MAX_HOPS
    )
    graph.index(docs)
    _, source_trace = graph.retrieve_with_trace(query, len(docs))
    paths = source_trace["paths"]

    # No graph evidence means exact identity, not re-tie-breaking.
    if not paths:
        return GraphHybridComparison(
            baseline, baseline.copy(),
            {
                "policy_id": POLICY["policy_id"],
                "policy_sha256": policy_fingerprint(),
                "graph_activated": False,
                "paths": [],
                "boosted_document_ids": [],
                "baseline_document_ids": [r.doc_id for r in baseline],
                "candidate_document_ids": [r.doc_id for r in baseline],
                "gold_labels_used": False,
                "semantic_support_verified": False,
            },
        )
    edges_by_id = {edge.id: edge for edge in edges}
    # The shortest supported path to each ORIGINAL source caps the boost.
    min_depth: dict[str, int] = {}
    for path in paths:
        for hop, edge_id in enumerate(path["edge_ids"], start=1):
            doc_id = edges_by_id[edge_id].document_id
            min_depth[doc_id] = min(min_depth.get(doc_id, MAX_HOPS + 1), hop)
    scores = {
        result.doc_id: result.score + (
            GRAPH_BONUS_WEIGHT / (RRF_CONSTANT + min_depth[result.doc_id])
            if result.doc_id in min_depth else 0.0
        ) for result in complete
    }
    selected = sorted(scores, key=lambda doc_id: (-scores[doc_id], doc_id))[:k]
    ranked = [
        SearchResult(doc_id=doc_id, score=scores[doc_id], rank=i)
        for i, doc_id in enumerate(selected, start=1)
    ]
    return GraphHybridComparison(
        baseline, ranked,
        {
            "policy_id": POLICY["policy_id"],
            "policy_sha256": policy_fingerprint(),
            "graph_activated": True,
            "paths": paths,
            "boosted_document_ids": sorted(min_depth),
            "min_hops_by_document": dict(sorted(min_depth.items())),
            "baseline_document_ids": [r.doc_id for r in baseline],
            "candidate_document_ids": [r.doc_id for r in ranked],
            "gold_labels_used": False,
            "semantic_support_verified": False,
        },
    )


def lock_policy_manifest(cohort_path: Path, output: Path) -> dict[str, Any]:
    """Seal cohort and policy before any evaluation or model inference."""
    cohort = json.loads(cohort_path.read_text(encoding="utf-8"))
    ids = cohort.get("reserved_query_ids")
    if (
        cohort.get("schema_version") != 1
        or cohort.get("cohort_id") != COHORT_SCHEMA
        or cohort.get("status") != "reserved_not_evaluated"
        or cohort.get("dataset_sha256") != HOTPOT_SHA256
        or cohort.get("prior_exposed_run_sha256") != PREVIOUS_STUDY_SHA256
        or cohort.get("overlap_count_with_grf00") != 0
        or cohort.get("evaluation_scores") is not None
        or not isinstance(ids, list) or len(ids) != 60
        or any(not isinstance(q, str) or not q for q in ids)
        or len(set(ids)) != 60
    ):
        raise ValueError("Unverified or already scored GRF-01 evaluation cohort")
    digest = hashlib.sha256("\n".join(ids).encode("utf-8")).hexdigest()
    if digest != EXPECTED_COHORT_SHA256 or cohort.get("reserved_query_ids_sha256") != digest:
        raise ValueError("Reserved cohort fingerprint mismatch")
    manifest = {
        "schema_version": 1,
        "status": "policy_locked_before_evaluation",
        "cohort_id": COHORT_SCHEMA,
        "cohort_query_ids_sha256": digest,
        "cohort_size": len(ids),
        "policy": POLICY,
        "policy_sha256": policy_fingerprint(),
        "model_weights_loaded": False,
        "scores_computed": False,
        "benchmark_run": False,
        "limitations": [
            "The disjoint DEV cohort is not a fully independent new dataset.",
            "Fixed title-mention graph features are lexical, not semantic evidence verification.",
            "Actual benchmark must account for relation-building time, model embedding/index costs.",
            "No claim of benefit, accuracy or model quality is supported by this policy file.",
        ],
    }
    serialized = json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        if output.read_text(encoding="utf-8") != serialized:
            raise ValueError("Existing locked policy differs; refusing overwrite")
    else:
        output.write_text(serialized, encoding="utf-8")
    return manifest


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(
        description="Freeze reproducible Graph-Hybrid policy; never evaluates DEV cohort"
    )
    parser.add_argument(
        "--cohort", default="runs/graph-hybrid/GRF01_RESERVED_DEV_COHORT.json"
    )
    parser.add_argument(
        "--output", default="runs/graph-hybrid/GRF01_POLICY_LOCK.json"
    )
    args = parser.parse_args()
    result = lock_policy_manifest(Path(args.cohort), Path(args.output))
    print("GRF01_GRAPH_HYBRID_POLICY_LOCKED")
    print(f"GRF01_MODEL_ID={EMBEDDING_MODEL}")
    print(f"GRF01_MODEL_REVISION={EMBEDDING_REVISION}")
    print(f"GRF01_POLICY_SHA256={result['policy_sha256']}")
    print(f"GRF01_COHORT_SHA256={result['cohort_query_ids_sha256']}")
    print(f"GRF01_POLICY_MANIFEST={args.output}")
    print("No models downloaded, no reserved query scored, no default changed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
