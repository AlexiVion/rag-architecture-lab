"""Offline-reproducible paired IR evaluation on original HotpotQA distractor DEV.

This measures whether a document-title link graph improves document retrieval,
NOT whether GraphRAG improves answer quality or factuality. The retriever has
zero access to supporting-fact labels; they are used only in metrics afterward.
"""
from __future__ import annotations

import hashlib
import json
import math
import random
import re
import statistics
import time
import urllib.request
from pathlib import Path
from typing import Any

from raglab.core import Document
from raglab.graph import EvidenceEdge, EvidenceGraphRetriever, GraphNode
from raglab.retrieval import BM25Retriever

# This is a checksum-identical mirror of the official HotpotQA dev distractor
# archive (not a changed or a test-split file). Official original checksum:
# https://huggingface.co/datasets/hotpotqa/hotpot_qa/blob/cb440e4e72efe5808fe5df497ffa0b4e8da85c32/dataset_infos.json
HOTPOT_URL = (
    "https://huggingface.co/datasets/RAGLAB/data/resolve/main/"
    "eval_datasets/HotPotQA/hotpot_dev_distractor_v1.json"
)
HOTPOT_SHA256 = "4e9ecb5c8d3b719f624d66b60f8d56bf227f03914f5f0753d6fa1b359d7104ea"
MAX_DOWNLOAD_BYTES = 60_000_000
DATASET_ID = "hotpotqa/distractor/dev_v1"


def cached_hotpotqa(path: Path) -> Path:
    """Download once, SHA-verify each use, and never silently overwrite a cache."""
    if path.exists():
        if hashlib.sha256(path.read_bytes()).hexdigest() != HOTPOT_SHA256:
            raise ValueError("HotpotQA cache checksum mismatch; refusing changed data")
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    part = path.with_name(path.name + ".part")
    if part.exists():
        raise FileExistsError("Stale partial download exists; refusing to overwrite")
    try:
        request = urllib.request.Request(
            HOTPOT_URL, headers={"User-Agent": "rag-architecture-lab/0.1"}
        )
        with urllib.request.urlopen(request, timeout=90) as response:
            with part.open("xb") as output:
                count = 0
                while chunk := response.read(1024 * 1024):
                    count += len(chunk)
                    if count > MAX_DOWNLOAD_BYTES:
                        raise ValueError("HotpotQA download exceeds safety budget")
                    output.write(chunk)
        if hashlib.sha256(part.read_bytes()).hexdigest() != HOTPOT_SHA256:
            raise ValueError("Downloaded HotpotQA data does not match the pinned hash")
        part.replace(path)
    except BaseException:
        if part.exists():
            part.unlink()
        raise
    return path


def load_bridge_dev_rows(path: Path, *, seed: int = 17, count: int = 60) -> list[dict]:
    """Choose a deterministic bridge-question subset without reading test data."""
    if not 1 <= count <= 500:
        raise ValueError("count must be between 1 and 500")
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("Expected original HotpotQA distractor DEV JSON array")
    eligible: list[dict] = []
    seen: set[str] = set()
    for record in raw:
        if not isinstance(record, dict) or record.get("type") != "bridge":
            continue
        question_id = record.get("_id")
        question = record.get("question")
        ctx = record.get("context")
        sf = record.get("supporting_facts")
        if not isinstance(question_id, str) or not isinstance(question, str):
            raise ValueError("Malformed HotpotQA DEV bridge question")
        if question_id in seen:
            raise ValueError("Duplicate HotpotQA question ID")
        seen.add(question_id)
        if not isinstance(ctx, list) or not isinstance(sf, list):
            raise ValueError("Malformed HotpotQA context or supporting facts")
        titles = [
            part[0] for part in ctx
            if isinstance(part, list) and len(part) == 2 and isinstance(part[0], str)
        ]
        if len(titles) != len(ctx) or len(set(titles)) != len(ctx):
            continue  # Explicitly exclude malformed or duplicate-title contexts.
        gold = {
            fact[0] for fact in sf if isinstance(fact, list)
            and len(fact) == 2 and isinstance(fact[0], str)
        }
        # Eligibility requires genuinely two-document, in-context support.
        # Gold is NEVER used to construct edges, rank docs or pick graph seeds.
        if len(gold) < 2 or not gold.issubset(set(titles)):
            continue
        eligible.append(record)
    eligible.sort(
        key=lambda row: (
            hashlib.sha256(f"{seed}|{row['_id']}".encode("utf-8")).hexdigest(),
            row["_id"],
        )
    )
    if len(eligible) < count:
        raise ValueError(f"Only {len(eligible)} valid bridge cases; requested {count}")
    return eligible[:count]


def case_documents(row: dict) -> tuple[list[Document], dict[str, str], set[str]]:
    """Convert candidate paragraphs to retrieval documents; no stance leakage."""
    docs: list[Document] = []
    title_to_id: dict[str, str] = {}
    for index, pair in enumerate(row["context"]):
        title, sentences = pair
        if not isinstance(sentences, list) or not all(isinstance(s, str) for s in sentences):
            raise ValueError("Invalid HotpotQA context sentence list")
        doc_id = f"paragraph-{index:02d}"
        title_to_id[title] = doc_id
        docs.append(Document(id=doc_id, title=title, text=" ".join(sentences)))
    gold_ids = {title_to_id[fact[0]] for fact in row["supporting_facts"]}
    return docs, title_to_id, gold_ids


def derive_title_link_graph(documents: list[Document]) -> tuple[list[GraphNode], list[EvidenceEdge]]:
    """Build text-supported 'mentions' edges without inspecting gold qrels.

    Node = a candidate paragraph's article title; edge = a sentence of article
    A explicitly mentioning the title of article B. This graph has no learned
    entity extraction and is not supervised by supporting-fact labels.
    """
    nodes = [GraphNode(id=doc.id, label=doc.title) for doc in documents]
    edges: list[EvidenceEdge] = []
    for i, source in enumerate(documents):
        for j, target in enumerate(documents):
            if i == j or len(target.title.strip()) < 4:
                continue
            pattern = re.compile(
                r"(?<!\w)" + re.escape(target.title) + r"(?!\w)", re.IGNORECASE
            )
            # HotpotQA context stores sentence boundaries; the parsed Document
            # uses joined sentences, so matched source strings remain verbatim.
            for sentence in source.text.split(". "):
                quoted = sentence.strip()
                if quoted and pattern.search(quoted):
                    edges.append(EvidenceEdge(
                        id=f"link-{i:02d}-{j:02d}",
                        source=source.id,
                        relation="mentions",
                        target=target.id,
                        document_id=source.id,
                        quote=quoted,
                    ))
                    break
    return nodes, edges


def recall_at_k(doc_ids: list[str], gold: set[str], k: int) -> float:
    if not gold or k < 1:
        raise ValueError("Nonempty gold IDs and positive k required")
    return len(set(doc_ids[:k]) & gold) / len(gold)


def _bootstrap_ci(deltas: list[float], *, seed: int, replicates: int = 1000) -> tuple[float, float]:
    if not deltas:
        raise ValueError("Bootstrap sample cannot be empty")
    rng = random.Random(seed)
    n = len(deltas)
    draws = sorted(
        statistics.fmean(deltas[rng.randrange(n)] for _ in range(n))
        for _ in range(replicates)
    )
    return (draws[int(0.025 * replicates)], draws[int(0.975 * replicates)])


def benchmark_bridge_dev(
    records: list[dict], *, seed: int = 17, ks: tuple[int, ...] = (1, 3, 5)
) -> dict[str, Any]:
    """Paired context-constrained retrieval benchmark; no generation occurs."""
    if not records or not ks or min(ks) < 1:
        raise ValueError("At least one case and positive k are required")
    ks = tuple(sorted(set(ks)))
    rows: list[dict[str, Any]] = []
    for record in records:
        docs, title_ids, gold = case_documents(record)
        nodes, edges = derive_title_link_graph(docs)
        sparse = BM25Retriever()
        graph = EvidenceGraphRetriever(
            BM25Retriever(), nodes=nodes, edges=edges, max_hops=2
        )
        began = time.perf_counter()
        sparse.index(docs)
        bm_index_ms = (time.perf_counter() - began) * 1000
        began = time.perf_counter()
        graph.index(docs)
        gr_index_ms = (time.perf_counter() - began) * 1000
        question = record["question"]
        top = min(max(ks), len(docs))
        began = time.perf_counter()
        bm = sparse.retrieve(question, top)
        bm_query_ms = (time.perf_counter() - began) * 1000
        began = time.perf_counter()
        gr, trace = graph.retrieve_with_trace(question, top)
        gr_query_ms = (time.perf_counter() - began) * 1000
        bm_ids = [entry.doc_id for entry in bm]
        gr_ids = [entry.doc_id for entry in gr]
        baseline = {f"recall@{k}": recall_at_k(bm_ids, gold, k) for k in ks}
        candidate = {f"recall@{k}": recall_at_k(gr_ids, gold, k) for k in ks}
        row = {
            "question_id": record["_id"],
            "question_type": record["type"],
            "question_level": record.get("level"),
            "question": question,
            "candidate_count": len(docs),
            "gold_supporting_document_ids": sorted(gold),
            "gold_supporting_titles": sorted([name for name, did in title_ids.items() if did in gold]),
            "graph_node_count": len(nodes),
            "graph_edge_count": len(edges),
            "graph_seed_count": len(trace["seed_entity_ids"]),
            "graph_path_count": len(trace["paths"]),
            "baseline": baseline,
            "candidate": candidate,
            "baseline_ranked_titles": [
                next((name for name, did in title_ids.items() if did == didx), didx)
                for didx in bm_ids
            ],
            "candidate_ranked_titles": [
                next((name for name, did in title_ids.items() if did == didx), didx)
                for didx in gr_ids
            ],
            "timing_ms": {
                "bm25_index": bm_index_ms, "graph_index_with_bm25": gr_index_ms,
                "bm25_query": bm_query_ms, "graph_query": gr_query_ms,
            },
        }
        rows.append(row)
    summary: dict[str, Any] = {}
    for k in ks:
        key = f"recall@{k}"
        base = [row["baseline"][key] for row in rows]
        cand = [row["candidate"][key] for row in rows]
        diffs = [c - b for c, b in zip(cand, base, strict=True)]
        lo, hi = _bootstrap_ci(diffs, seed=seed + k)
        summary[key] = {
            "bm25": statistics.fmean(base),
            "graph_plus_bm25": statistics.fmean(cand),
            "paired_delta": statistics.fmean(diffs),
            "paired_bootstrap_95ci": [lo, hi],
            "wins": sum(d > 0 for d in diffs),
            "losses": sum(d < 0 for d in diffs),
            "ties": sum(d == 0 for d in diffs),
        }
    return {
        "schema_version": 1,
        "experiment_id": "GRF00-HOTPOTQA-DEV-01",
        "dataset": DATASET_ID,
        "dataset_source": HOTPOT_URL,
        "dataset_sha256": HOTPOT_SHA256,
        "dataset_license": "CC BY-SA 4.0 (not MIT; see source attribution)",
        "split": "dev/distractor",
        "subset": "bridge questions with >=2 gold supporting titles present among supplied distractor contexts",
        "sample_seed": seed,
        "sample_count": len(rows),
        "architecture_baseline": "BM25 on per-question distractor candidate set",
        "architecture_candidate": "source-quoted article-title links, 2-hop graph-first + BM25 fallback",
        "graph_built_without_gold_labels": True,
        "retrieval_scope": "per-question provided distractor contexts; NOT full Wikipedia",
        "relevance_target": "supporting document recall, not answer generation/faithfulness",
        "metrics": summary,
        "cases_with_graph_seeds": sum(row["graph_seed_count"] > 0 for row in rows),
        "cases_with_graph_edges": sum(row["graph_edge_count"] > 0 for row in rows),
        "mean_index_ms": {
            "bm25": statistics.fmean(row["timing_ms"]["bm25_index"] for row in rows),
            "graph_plus_bm25": statistics.fmean(row["timing_ms"]["graph_index_with_bm25"] for row in rows),
        },
        "mean_query_ms": {
            "bm25": statistics.fmean(row["timing_ms"]["bm25_query"] for row in rows),
            "graph_plus_bm25": statistics.fmean(row["timing_ms"]["graph_query"] for row in rows),
        },
        "limitations": [
            "A small, deterministic sample of HotpotQA DEV bridge questions; no parameter search.",
            "Per-question distractor setting is much easier than corpus-wide retrieval.",
            "Gold supporting facts are used for selecting eligible queries and scoring only.",
            "Graph edges are unsupervised lexical title mentions, not semantic relations.",
            "Scores do not measure answer correctness, entailment, or retrieval over open Wikipedia.",
            "Index and query timings are sequential CPU measurements, not warmed production p95.",
            "Candidate graph can be empty or fail to help; negative results are retained.",
            "Do not tune algorithm parameters using this reported DEV sample.",
            "Results are research artifacts, not permission to redistribute original HotpotQA text.",
        ],
        "queries": rows,
    }


def report_markdown(result: dict[str, Any]) -> str:
    lines = [
        "# GRF-00 — HotpotQA distractor DEV: Graph + BM25 vs BM25",
        "",
        f"Dataset: {result['dataset']} — **{result['sample_count']}** bridge questions",
        "Original HotpotQA dataset: CC BY-SA 4.0; no trained models or generation.",
        "",
        "| Metric | BM25 | Graph+BM25 | Delta | 95% paired bootstrap CI | W/L/T |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for metric, stats in result["metrics"].items():
        lo, hi = stats["paired_bootstrap_95ci"]
        lines.append(
            f"| {metric} | {stats['bm25']:.4f} | {stats['graph_plus_bm25']:.4f} "
            f"| {stats['paired_delta']:+.4f} | [{lo:+.4f}, {hi:+.4f}] "
            f"| {stats['wins']}/{stats['losses']}/{stats['ties']} |"
        )
    lines += [
        "",
        f"Graph-seeded cases: {result['cases_with_graph_seeds']}/{result['sample_count']}.",
        f"Cases with constructed title-mention edges: {result['cases_with_graph_edges']}/{result['sample_count']}.",
        "",
        "## Scientific boundaries",
        "",
    ]
    lines += ["- " + note for note in result["limitations"]]
    return "\n".join(lines) + "\n"


def main() -> int:
    import argparse
    from datetime import UTC, datetime

    parser = argparse.ArgumentParser(
        description="Paired HotpotQA DEV graph-vs-BM25 retrieval research (NO generators)"
    )
    parser.add_argument("--cache", default=".cache/hotpotqa/hotpot_dev_distractor_v1.json")
    parser.add_argument("--output-dir", default="runs/graph-hotpotqa")
    parser.add_argument("--count", type=int, default=60)
    parser.add_argument("--seed", type=int, default=17)
    args = parser.parse_args()
    data_path = cached_hotpotqa(Path(args.cache))
    cases = load_bridge_dev_rows(data_path, seed=args.seed, count=args.count)
    result = benchmark_bridge_dev(cases, seed=args.seed)
    result["sample_query_ids_sha256"] = hashlib.sha256(
        "\n".join(record["_id"] for record in cases).encode("utf-8")
    ).hexdigest()
    result["created_at_utc"] = datetime.now(UTC).isoformat()
    folder = Path(args.output_dir)
    folder.mkdir(parents=True, exist_ok=True)
    suffix = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    json_file = folder / f"GRF00_HOTPOTQA_{suffix}.json"
    md_file = folder / f"GRF00_HOTPOTQA_{suffix}.md"
    with json_file.open("x", encoding="utf-8") as output:
        json.dump(result, output, ensure_ascii=False, indent=2)
    with md_file.open("x", encoding="utf-8") as output:
        output.write(report_markdown(result))
    print(f"Dataset: {result['dataset']}; selected DEV bridge cases: {result['sample_count']}")
    print(f"Cases with graph seeds: {result['cases_with_graph_seeds']}")
    print(f"Cases with any graph edges: {result['cases_with_graph_edges']}")
    for metric, stats in result["metrics"].items():
        print(
            f"{metric}: BM25={stats['bm25']:.4f} "
            f"Graph+BM25={stats['graph_plus_bm25']:.4f} "
            f"delta={stats['paired_delta']:+.4f} "
            f"CI95={stats['paired_bootstrap_95ci']}"
        )
    print(f"JSON: {json_file}")
    print(f"Markdown: {md_file}")
    print("GRF00_HOTPOTQA_DEV_PAIRED_RETRIEVAL_COMPLETED")
    print("No generative model, semantic accuracy or held-out TEST data evaluated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
