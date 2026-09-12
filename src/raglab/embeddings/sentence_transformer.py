from __future__ import annotations

from collections.abc import Sequence

import numpy as np
from numpy.typing import NDArray


class SentenceTransformerEmbeddings:
    """Thin adapter around a local Sentence Transformers model.

    The embedding model is intentionally treated as a dependency. Retrieval,
    indexing, scoring and evaluation remain implemented by this project.
    """

    def __init__(
        self,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        batch_size: int = 64,
    ) -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:  # pragma: no cover - dependency error path
            raise RuntimeError(
                'Dense retrieval requires the optional dependency. Run: pip install -e ".[benchmark]"'
            ) from exc

        self.name = model_name
        self.batch_size = batch_size
        self._model = SentenceTransformer(model_name)

    def encode(self, texts: Sequence[str]) -> NDArray[np.float32]:
        vectors = self._model.encode(
            list(texts),
            batch_size=self.batch_size,
            show_progress_bar=len(texts) > self.batch_size,
            convert_to_numpy=True,
            normalize_embeddings=False,
        )
        return np.asarray(vectors, dtype=np.float32)
