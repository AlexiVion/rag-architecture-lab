from __future__ import annotations


class LocalTransformersGenerator:
    """Small local instruction-model wrapper used for zero-API-cost V2 experiments."""

    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
        self.name = f"transformers:{model_name}"
        self._tokenizer = None
        self._model = None

    def _load(self) -> None:
        if self._tokenizer is not None and self._model is not None:
            return

        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer
        except ImportError as exc:  # pragma: no cover - dependency error path
            raise RuntimeError(
                'Local generation requires the generation extra. Run: pip install -e ".[generation]"'
            ) from exc

        tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        model = AutoModelForCausalLM.from_pretrained(
            self.model_name,
            torch_dtype="auto",
        )
        model.eval()
        self._tokenizer = tokenizer
        self._model = model

    def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        max_new_tokens: int = 220,
    ) -> str:
        if max_new_tokens <= 0:
            raise ValueError("max_new_tokens must be positive")

        self._load()
        tokenizer = self._tokenizer
        model = self._model
        assert tokenizer is not None
        assert model is not None

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        try:
            prompt = tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
            )
        except (AttributeError, ValueError):
            prompt = f"SYSTEM:\n{system_prompt}\n\nUSER:\n{user_prompt}\n\nASSISTANT:\n"

        inputs = tokenizer(prompt, return_tensors="pt")
        input_length = int(inputs["input_ids"].shape[1])

        import torch

        with torch.inference_mode():
            output = model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                do_sample=False,
                pad_token_id=tokenizer.eos_token_id,
            )

        generated_tokens = output[0][input_length:]
        return tokenizer.decode(generated_tokens, skip_special_tokens=True).strip()
