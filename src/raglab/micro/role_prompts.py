"""Frozen task-formatted prompts for tiny base and instruction-tuned models.

This is a DEV-only diagnostic; prompt optimization on SQuAD DEV creates tuning
contamination. Never report it as independent generalization. In particular,
base causal LMs should not be assumed to understand artificial SYSTEM/USER
chat delimiters when they were not trained on that instruction format.
"""

from __future__ import annotations

from typing import Any


def question_and_evidence(user_prompt: str) -> tuple[str, str]:
    prefix = "Question:\n"
    divider = "\n\nEvidence:\n"
    suffix = "\n\nIf there is insufficient evidence, abstain."
    if not user_prompt.startswith(prefix) or divider not in user_prompt:
        raise ValueError("Unexpected MICRO question/evidence prompt contract")
    question, remainder = user_prompt[len(prefix):].split(divider, 1)
    if suffix not in remainder:
        raise ValueError("Unexpected MICRO evidence prompt suffix")
    evidence = remainder.split(suffix, 1)[0]
    if not question.strip():
        raise ValueError("Empty QA prompt")
    return question.strip(), evidence.strip()


def base_completion_prompt(question: str, evidence: str) -> str:
    """Two frozen synthetic few-shot examples, never SQuAD gold examples."""
    return (
        "Read the passage. Give the shortest answer in the passage. "
        "If no answer is stated, write INSUFFICIENT_EVIDENCE.\n\n"
        "Passage: [S1] The silver comet was named Caldor.\n"
        "Question: What was the comet named?\n"
        "Answer: Caldor\n\n"
        "Passage: [S1] The garden contains twelve trees.\n"
        "Question: What is the gardener's name?\n"
        "Answer: INSUFFICIENT_EVIDENCE\n\n"
        f"Passage: {evidence}\n"
        f"Question: {question}\n"
        "Answer:"
    )


def instruction_chat_system() -> str:
    return (
        "You answer short factual questions. Use only the provided passage. "
        "Return a short exact answer phrase with no citation, explanation or "
        "restatement. When the passage does not contain an answer, return "
        "INSUFFICIENT_EVIDENCE."
    )


def instruction_chat_user(question: str, evidence: str) -> str:
    return f"Passage:\n{evidence}\n\nQuestion:\n{question}\n\nAnswer:"


class RoleAdaptedQAGenerator:
    """Uses an actual completion prompt for a base LM or chat for instruct LM.

    A single frozen prompt per model class: no dynamic generation of examples,
    learned prompt tuning or switching prompts based on answer annotations.
    """

    def __init__(self, original: Any, *, model_role: str) -> None:
        if model_role not in {"base", "instruct"}:
            raise ValueError("model_role must be base or instruct")
        self.inner = original
        self.role = model_role
        self.name = original.name + f":frozen-role-qa-{model_role}-v1"
        self.full_prompt_token_counts: list[int] = []

    def count_tokens(self, text: str) -> int:
        return self.inner.count_tokens(text)

    def generate(
        self, *, system_prompt: str, user_prompt: str, max_new_tokens: int = 24
    ) -> str:
        # This deliberately ignores the universal MICRO chat boilerplate and
        # substitutes a recorded model-family-appropriate task prompt.
        _ = system_prompt
        if max_new_tokens <= 0:
            raise ValueError("max_new_tokens must be positive")
        question, evidence = question_and_evidence(user_prompt)
        self.inner._load()
        tokenizer = self.inner._tokenizer
        model = self.inner._model
        assert tokenizer is not None and model is not None
        if self.role == "base":
            prompt = base_completion_prompt(question, evidence)
        else:
            if not hasattr(tokenizer, "apply_chat_template"):
                raise RuntimeError("Instruction model tokenizer has no chat template")
            prompt = tokenizer.apply_chat_template(
                [
                    {"role": "system", "content": instruction_chat_system()},
                    {"role": "user", "content": instruction_chat_user(question, evidence)},
                ],
                tokenize=False,
                add_generation_prompt=True,
            )
        inputs = tokenizer(prompt, return_tensors="pt")
        length = int(inputs["input_ids"].shape[1])
        self.full_prompt_token_counts.append(length)

        import torch

        with torch.inference_mode():
            output = model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                do_sample=False,
                pad_token_id=tokenizer.eos_token_id,
            )
        return tokenizer.decode(
            output[0][length:], skip_special_tokens=True
        ).strip()
