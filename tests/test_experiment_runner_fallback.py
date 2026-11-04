from __future__ import annotations

import numpy as np

from raglab.core import Document, Query
from raglab.datasets import BenchmarkDataset
from raglab.experiments import run_experiment


class ToyEmbeddings:
    name = "toy"

    def encode(self, texts):
        def vector(text):
            text = text.lower()
            return [float("apple" in text), float("banana" in text)]
        return np.asarray([vector(text) for text in texts], dtype=np.float32)


def test_corrective_can_select_dense_fallback_with_injected_embeddings() -> None:
    dataset = BenchmarkDataset(
        id="toy",
        documents=[Document("a", "apple"), Document("b", "banana")],
        queries=[Query("q", "apple")],
        qrels={"q": {"a": 1}},
    )
    result = run_experiment(
        {
            "experiment_id": "RET-07-test",
            "base": "bm25",
            "architecture": "corrective",
            "k": [1],
            "params": {"min_primary_score": 999.0, "fallback_base": "dense"},
        },
        dataset=dataset,
        embeddings=ToyEmbeddings(),
    )
    assert result["configuration"]["embedding_model"]
    assert result["results"][1]["pipeline"] == "corrective"
