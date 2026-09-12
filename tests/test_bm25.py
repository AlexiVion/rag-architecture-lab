from raglab.core import Document
from raglab.retrieval.bm25 import BM25Retriever


def test_bm25_prefers_exact_lexical_match() -> None:
    retriever = BM25Retriever()
    retriever.index(
        [
            Document(id="a", text="neural retrieval systems and embeddings"),
            Document(id="b", text="classical cooking recipes and ingredients"),
            Document(id="c", text="retrieval augmented generation with neural search"),
        ]
    )

    results = retriever.retrieve("neural retrieval", k=3)
    assert results[0].doc_id in {"a", "c"}
    assert results[-1].doc_id == "b"
