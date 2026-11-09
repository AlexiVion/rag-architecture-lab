"""Candidate registry, not a model benchmark or redistribution/license certification.

Every checkpoint must be pinned, rights-checked and locally measured before it
can become a canonical scientific result. None are downloaded by this module.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True, slots=True)
class ModelCandidate:
    key: str
    repository: str
    parameters_millions: float
    role: str
    architecture: str
    license_claim: str
    license_review: str = "PENDING_EXACT_REVISION_REVIEW"
    revision: str | None = None
    measured: bool = False

    def as_dict(self) -> dict:
        return asdict(self)


CANDIDATES: tuple[ModelCandidate, ...] = (
    ModelCandidate(
        "tinystories-1m",
        "roneneldan/TinyStories-Instruct-1M",
        1,
        "restricted_domain_generator",
        "causal_lm",
        "VERIFY_CHECKPOINT_RIGHTS",
    ),
    ModelCandidate(
        "pythia-14m",
        "EleutherAI/pythia-14m",
        14,
        "base_language_model_not_instruct",
        "causal_lm",
        "Apache-2.0",
    ),
    ModelCandidate(
        "pythia-31m",
        "EleutherAI/pythia-31m",
        31,
        "base_language_model_not_instruct",
        "causal_lm",
        "Apache-2.0",
    ),
    ModelCandidate(
        "pythia-70m",
        "EleutherAI/pythia-70m",
        70,
        "base_language_model_not_instruct",
        "causal_lm",
        "Apache-2.0",
    ),
    ModelCandidate(
        "smollm2-135m",
        "HuggingFaceTB/SmolLM2-135M-Instruct",
        135,
        "instruction_generator",
        "causal_lm",
        "Apache-2.0",
    ),
    ModelCandidate(
        "smollm2-360m",
        "HuggingFaceTB/SmolLM2-360M-Instruct",
        360,
        "instruction_generator",
        "causal_lm",
        "Apache-2.0",
    ),
    ModelCandidate(
        "qwen25-05b",
        "Qwen/Qwen2.5-0.5B-Instruct",
        500,
        "instruction_generator",
        "causal_lm",
        "Apache-2.0",
    ),
    ModelCandidate(
        "qwen3-06b",
        "Qwen/Qwen3-0.6B",
        600,
        "instruction_generator",
        "causal_lm",
        "Apache-2.0",
    ),
)


def get_candidate(key: str) -> ModelCandidate:
    for candidate in CANDIDATES:
        if candidate.key == key:
            return candidate
    raise KeyError(f"Unknown model candidate: {key!r}")


def registry_manifest() -> dict:
    return {
        "schema_version": 1,
        "status": "proposed_unmeasured",
        "model_revisions_pinned": False,
        "model_downloads_performed": False,
        "candidates": [candidate.as_dict() for candidate in CANDIDATES],
        "limitations": [
            "Parameter totals are model-family approximations, not measurements",
            "All licenses and exact revisions require independent verification",
            "A base language model is not an instruction-following assistant",
            "TinyStories 1M is restricted-domain, not demonstrated open-domain RAG",
            "No measured tiny-model performance is implied by this registry",
        ],
    }
