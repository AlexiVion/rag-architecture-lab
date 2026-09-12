from __future__ import annotations

from dataclasses import dataclass

from raglab.core import Document, Query


@dataclass(slots=True)
class BenchmarkDataset:
    id: str
    documents: list[Document]
    queries: list[Query]
    qrels: dict[str, dict[str, int]]


def load_ir_dataset(dataset_id: str, limit_queries: int | None = None) -> BenchmarkDataset:
    """Load an ir_datasets benchmark into the lab's small internal data model."""
    try:
        import ir_datasets
    except ImportError as exc:  # pragma: no cover - dependency error path
        raise RuntimeError(
            'Benchmark datasets require the optional dependency. Run: pip install -e ".[benchmark]"'
        ) from exc

    dataset = ir_datasets.load(dataset_id)

    if not dataset.has_docs() or not dataset.has_queries() or not dataset.has_qrels():
        raise ValueError(
            f"Dataset {dataset_id!r} must expose documents, queries, and qrels for evaluation."
        )

    documents: list[Document] = []
    for doc in dataset.docs_iter():
        title = str(getattr(doc, "title", "") or "")
        text = str(getattr(doc, "text", "") or "")
        if not text:
            raise ValueError(
                f"Dataset {dataset_id!r} contains documents without a 'text' field. "
                "Add a dataset-specific adapter before using it."
            )
        documents.append(Document(id=str(doc.doc_id), title=title, text=text))

    qrels: dict[str, dict[str, int]] = {}
    for qrel in dataset.qrels_iter():
        relevance = int(qrel.relevance)
        if relevance <= 0:
            continue
        qrels.setdefault(str(qrel.query_id), {})[str(qrel.doc_id)] = relevance

    queries = [
        Query(id=str(query.query_id), text=str(query.text))
        for query in dataset.queries_iter()
        if str(query.query_id) in qrels
    ]

    if limit_queries is not None:
        if limit_queries <= 0:
            raise ValueError("limit_queries must be positive")
        queries = queries[:limit_queries]

    if not documents or not queries or not qrels:
        raise ValueError(f"Dataset {dataset_id!r} did not produce an evaluable benchmark.")

    return BenchmarkDataset(
        id=dataset_id,
        documents=documents,
        queries=queries,
        qrels=qrels,
    )
