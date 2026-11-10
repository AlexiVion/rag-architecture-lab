"""Optional CPU-only pairwise NLI conflict diagnostics for extracted claims.

Raw model NLI scores are NOT calibrated evidence truth or factual reliability.
The scorer is permitted to surface provisional conflict traces but NEVER to
promote unsupported free-text extracts to a publishable ANSWER.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Protocol

from raglab.micro_v02.contracts import EvidenceClaim

NLI_LABELS = ("contradiction", "entailment", "neutral")


@dataclass(frozen=True, slots=True)
class VerifierObservation:
    left_doc_id: str
    right_doc_id: str
    predicted_relation: str
    contradiction_score: float
    model_name: str
    inference_scope: str = "provisional_pairwise_nli_not_semantic_support"

    def to_dict(self) -> dict:
        return asdict(self)


class EvidenceVerifier(Protocol):
    name: str
    def inspect(
        self, question: str, claims: tuple[EvidenceClaim, ...]
    ) -> tuple[VerifierObservation, ...]: ...


class LocalNLIConflictVerifier:
    """Pinned/offline-only PyTorch CPU NLI with explicit label-order checks.

    Both directions are scored; the three-class logits are averaged AFTER
    softmax, following the externally evaluated Ragability diagnostic protocol.
    The inputs here are *model-extracted claims*, not author-provided oracles.
    Source verification remains a separate research gate.
    """
    name = "local_nli_conflict_diagnostic"

    def __init__(self, model_directory: str, *, max_claims: int = 8) -> None:
        if not 2 <= max_claims <= 16:
            raise ValueError("Bounded NLI claim budget must be 2..16")
        from transformers import AutoConfig, AutoModelForSequenceClassification, AutoTokenizer
        config = AutoConfig.from_pretrained(model_directory, local_files_only=True)
        labels = {
            int(k): str(v).casefold() for k, v in config.id2label.items()
        }
        if labels != {0:"contradiction",1:"entailment",2:"neutral"}:
            raise ValueError(f"Unexpected local NLI model class order: {labels}")
        self.tokenizer = AutoTokenizer.from_pretrained(
            model_directory, use_fast=True, local_files_only=True
        )
        self.model = AutoModelForSequenceClassification.from_pretrained(
            model_directory, local_files_only=True, use_safetensors=True
        ).to("cpu")
        self.model.eval()
        self.max_claims = max_claims

    def inspect(
        self, question: str, claims: tuple[EvidenceClaim, ...]
    ) -> tuple[VerifierObservation, ...]:
        import torch

        if len(claims) > self.max_claims:
            raise ValueError("NLI evidence claim budget exceeded")
        observations = []
        for i, left in enumerate(claims):
            for right in claims[i+1:]:
                if left.citation.doc_id == right.citation.doc_id:
                    continue
                qa_left = f"Question: {question}\\nAnswer: {left.text}"
                qa_right = f"Question: {question}\\nAnswer: {right.text}"
                with torch.inference_mode():
                    fwd = self.tokenizer(
                        qa_left, qa_right, truncation=True, max_length=512,
                        return_tensors="pt",
                    )
                    rev = self.tokenizer(
                        qa_right, qa_left, truncation=True, max_length=512,
                        return_tensors="pt",
                    )
                    first = torch.softmax(self.model(**fwd).logits.float(), dim=-1)[0]
                    second = torch.softmax(self.model(**rev).logits.float(), dim=-1)[0]
                    symmetric = ((first + second) / 2).tolist()
                if len(symmetric) != 3 or not all(
                    math.isfinite(p) for p in symmetric
                ):
                    raise ValueError("Nonfinite or malformed NLI model outputs")
                predicted = NLI_LABELS[
                    max(range(3), key=lambda index:symmetric[index])
                ]
                observations.append(VerifierObservation(
                    left.citation.doc_id, right.citation.doc_id,
                    predicted, float(symmetric[0]), self.name,
                ))
        return tuple(observations)
