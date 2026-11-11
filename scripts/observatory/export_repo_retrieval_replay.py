"""Run real offline Python retrievers on eight versioned research documents.

This is an engineering trace without relevance labels, NOT a SciFact benchmark.
No pretrained model, external download or paid API.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path

from raglab.architectures import ParentChildRetriever
from raglab.core import Document
from raglab.core.fingerprint import fingerprint_documents
from raglab.retrieval import BM25Retriever

ROOT = Path(__file__).resolve().parents[2]
DOCUMENT_PATHS = (
    "README.md", "docs/RESEARCH_STATUS.md", "docs/EXPERIMENT_PROTOCOL.md",
    "docs/MICRO_RAG_V02_SPEC.md", "benchmarks/V0_RESULTS.md",
    "benchmarks/V1_RESULTS.md", "benchmarks/V1_1_RESULTS.md",
    "docs/PAPER_01_MICRO_CPU_FRONTIER_PROTOCOL.md",
)
QUERIES = (
    ("q01", "How does BM25 compare with dense retrieval and hybrid RRF on SciFact?"),
    ("q02", "Why was cross-encoder reranking on CPU rejected at 50 candidates?"),
    ("q03", "What evidence verification, abstention and held-out evaluation remain unverified?"),
)
CODE_PATHS = (
    "src/raglab/retrieval/bm25.py",
    "src/raglab/architectures/parent_child.py",
    "src/raglab/core/types.py",
    "scripts/observatory/export_repo_retrieval_replay.py",
)


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def build_replay(root: Path = ROOT) -> dict:
    documents = []
    sources = []
    for rel in DOCUMENT_PATHS:
        file = root / rel
        raw = file.read_bytes()
        documents.append(Document(id=rel, title=rel.rsplit("/", 1)[-1].removesuffix(".md"), text=raw.decode("utf-8")))
        sources.append({
            "id": rel, "title": rel.rsplit("/", 1)[-1].removesuffix(".md").replace("_", " "),
            "sha256": digest(raw),
            "url": "https://github.com/AlexiVion/rag-architecture-lab/blob/main/" + rel,
        })
    bm25 = BM25Retriever(k1=1.5, b=0.75)
    parent = ParentChildRetriever(
        BM25Retriever(k1=1.5, b=0.75),
        chunk_chars=480, overlap_chars=60, candidate_k=100,
    )
    bm25.index(documents)
    parent.index(documents)
    queries = []
    for query_id, question in QUERIES:
        rankings = {}
        for name, retriever in (("bm25", bm25), ("parent_child_bm25", parent)):
            raw = retriever.retrieve(question, 5)
            if len(raw) != 5 or len({item.doc_id for item in raw}) != 5:
                raise ValueError("Invalid top-five ranking")
            if any(not math.isfinite(item.score) for item in raw):
                raise ValueError("Nonfinite score")
            rankings[name] = [
                {"doc_id": item.doc_id, "rank": item.rank, "score": round(item.score, 9)}
                for item in raw
            ]
        queries.append({
            "id": query_id, "text": question, "rankings": rankings,
            "qrels": None, "answer": None, "answer_evaluation": "not_evaluated",
        })
    return {
        "schema_version": 1,
        "kind": "repository_retrieval_execution",
        "status": "measured_software_trace_unlabelled",
        "dataset": "versioned_rag_lab_research_documents",
        "selection": "fixed_eight_documents_three_questions",
        "execution": {
            "software": "raglab Python retrievers",
            "pipelines": ["bm25", "parent_child_bm25"],
            "bm25": {"k1": 1.5, "b": 0.75},
            "parent_child": {"chunk_chars": 480, "overlap_chars": 60, "candidate_k": 100},
            "top_k": 5, "corpus_sha256": fingerprint_documents(documents),
            "code_sources": [
                {"path": rel, "sha256": digest((root / rel).read_bytes())}
                for rel in CODE_PATHS
            ],
        },
        "documents": sources,
        "queries": queries,
        "limitations": [
            "Real Python retrieval on versioned repository documents, not BEIR SciFact.",
            "Three authored teaching questions; no relevance labels or independent human review.",
            "No measured MRR, Recall, nDCG, answer accuracy, or neural model inference.",
            "BM25 full-document and child-passage scores have different scales; compare ranks, not score magnitudes.",
            "Small repository-specific corpus; numerical ties may depend on NumPy version.",
        ],
    }


def validate_replay(payload: dict, root: Path = ROOT) -> None:
    if payload.get("schema_version") != 1 or payload.get("kind") != "repository_retrieval_execution":
        raise ValueError("Unexpected replay schema")
    if payload.get("status") != "measured_software_trace_unlabelled":
        raise ValueError("An unlabelled trace must not claim benchmark validation")
    # Do not mistake harmless sub-micro floating-point differences across NumPy
    # builds for corrupted source data. Positions and fingerprints remain exact.
    expected = build_replay(root)
    import copy
    normalized = copy.deepcopy(payload)
    for case_actual, case_expected in zip(normalized.get("queries", []), expected["queries"]):
        for method in ("bm25", "parent_child_bm25"):
            for item_actual, item_expected in zip(
                case_actual.get("rankings", {}).get(method, []),
                case_expected["rankings"][method],
            ):
                score = item_actual.get("score")
                if (not isinstance(score, (float, int)) or isinstance(score, bool)
                    or not math.isfinite(score)
                    or not math.isclose(score, item_expected["score"], rel_tol=1e-7, abs_tol=1e-7)):
                    raise ValueError("Replay contains a changed retrieval score")
                item_actual["score"] = item_expected["score"]
    if normalized != expected:
        raise ValueError("Replay differs from source hashes or actual Python retrieval")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="experiments/repo_retrieval_replay.json")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    path = Path(args.output)
    if args.check:
        validate_replay(json.loads(path.read_text(encoding="utf-8")))
        print("REPOSITORY_REPLAY=VERIFIED")
        return
    payload = build_replay()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    print("REPOSITORY_REPLAY=EXPORTED")
    print("ARTIFACT=" + str(path))
    print("NO_QRELS_NO_SEMANTIC_VALIDATION=true")


if __name__ == "__main__":
    main()
