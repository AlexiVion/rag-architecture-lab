import numpy as np

from raglab.core import Document
from raglab.retrieval import BM25Retriever, DenseRetriever


class ToyEmbeddings:
    name = "toy"

    def encode(self, texts):
        vectors = {
            "apple": (1.0, 0.0),
            "banana": (0.0, 1.0),
            "apple query": (1.0, 0.0),
        }
        return np.asarray([vectors[text] for text in texts], dtype=np.float32)


def test_bm25_reindexes_when_document_text_changes_but_ids_do_not() -> None:
    retriever = BM25Retriever()
    retriever.index([Document("a", "apple"), Document("b", "banana")])
    assert retriever.retrieve("apple", 1)[0].doc_id == "a"
    retriever.index([Document("a", "banana"), Document("b", "apple")])
    assert retriever.retrieve("apple", 1)[0].doc_id == "b"


def test_dense_reindexes_when_document_text_changes_but_ids_do_not() -> None:
    retriever = DenseRetriever(ToyEmbeddings())
    retriever.index([Document("a", "apple"), Document("b", "banana")])
    assert retriever.retrieve("apple query", 1)[0].doc_id == "a"
    retriever.index([Document("a", "banana"), Document("b", "apple")])
    assert retriever.retrieve("apple query", 1)[0].doc_id == "b"
