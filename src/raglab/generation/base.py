from __future__ import annotations

from typing import Protocol


class Generator(Protocol):
    name: str

    def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        max_new_tokens: int = 220,
    ) -> str: ...
