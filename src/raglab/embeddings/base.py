from __future__ import annotations

from typing import Protocol, Sequence

import numpy as np
from numpy.typing import NDArray


class EmbeddingProvider(Protocol):
    name: str

    def encode(self, texts: Sequence[str]) -> NDArray[np.float32]: ...
