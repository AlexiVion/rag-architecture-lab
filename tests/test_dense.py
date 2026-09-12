import numpy as np

from raglab.core import Document
from raglab.retrieval.dense import DenseRetriever


class FakeEmbeddings:
    name = "fake"

    vectors = {
        "cats": np.array([1.0, 0.0], dtype=np.float32),
        "dogs": np.array([0.0, 1.0], dtype=np.float32),
        "cat query": np.array([0.9, 0.1], dtype=np.float32),
    }

    def encode(self, texts):
        return np.stack([self.vectors[text] for text in texts])


def test_dense_retrieval_uses_cosine_similarity() -> None:
    retriever = DenseRetriever(FakeEmbeddings())
    retriever.index([Document(id="cat", text="cats"), Document(id="dog", text="dogs")])
    results = retriever.retrieve("cat query", k=2)
    assert [result.doc_id for result in results] == ["cat", "dog"]
