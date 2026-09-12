from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

import numpy as np
from numpy.typing import NDArray


class EmbeddingProvider(Protocol):
    name: str

    def encode(self, texts: Sequence[str]) -> NDArray[np.float32]: ...
