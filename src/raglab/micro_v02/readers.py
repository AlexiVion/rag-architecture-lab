"""Source-safe optional readers for MICRO-RAG.

The strict default handles only explicit key:value evidence records and is a
transparent *zero-model baseline*, not a natural-language semantic extractor.
The optional real CPU QA reader uses a local checkpoint and MUST remain REVIEW
until separately source-supported/independently validated.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Protocol

from raglab.core import Document
from raglab.micro_v02.contracts import EvidenceCitation, EvidenceClaim


@dataclass(frozen=True, slots=True)
class QuestionSpec:
    entity: str
    field: str


class EvidenceReader(Protocol):
    name: str

    def extract(
        self, question: str, document: Document, spec: QuestionSpec | None
    ) -> EvidenceClaim | None: ...


_FIELD_ALIASES = {
    "start_year": (
        "start_year", "start year", "began operating", "started operating",
        "comenzó a operar", "empezó a operar", "año de inicio",
    ),
    "manager": ("manager", "manages", "responsable", "encargado"),
    "capacity": ("capacity", "capacidad"),
    "storage_seal": ("storage_seal", "storage seal", "sello de depósito"),
    "phase_marker": ("phase_marker", "phase marker", "marcador de fase"),
}
_ENTITY_RE = re.compile(
    r"(?iu)\b(?:station|estaci[oó]n)\s+([\w-]{2,40})\b"
)
_LINE_RE = re.compile(r"(?m)^([a-z_]+):[ \t]*([^\r\n]+?)[ \t]*$")


def parse_question(question: str) -> QuestionSpec | None:
    """Exact recognized field + named entity required; no inferred metadata."""
    entity_match = _ENTITY_RE.search(question)
    if not entity_match:
        return None
    lowered = question.casefold()
    matches = [
        field for field, aliases in _FIELD_ALIASES.items()
        if any(alias in lowered for alias in aliases)
    ]
    if len(matches) != 1:
        return None
    return QuestionSpec(entity=f"station {entity_match.group(1)}".casefold(), field=matches[0])


def _records(document: Document) -> dict[str, tuple[str, int, int]] | None:
    """Reject malformed, duplicate and ambiguous key fields, fail closed."""
    result: dict[str, tuple[str, int, int]] = {}
    for match in _LINE_RE.finditer(document.text):
        key = match.group(1).casefold()
        value = match.group(2).strip()
        if key in result or not value or len(value) > 160:
            return None
        start = match.start(2) + len(match.group(2)) - len(match.group(2).lstrip())
        end = start + len(value)
        result[key] = (value, start, end)
    if "entity" not in result:
        return None
    return result


def source_entity(document: Document) -> str | None:
    fields = _records(document)
    if fields is None:
        return None
    return fields["entity"][0].casefold()


class StructuredFactReader:
    """Conservative transparent baseline for explicit field:value evidence.

    The question must specify a known entity and property. This baseline must
    not be called natural-language reasoning over arbitrary documents.
    """
    name = "structured_literal"

    def extract(
        self, question: str, document: Document, spec: QuestionSpec | None
    ) -> EvidenceClaim | None:
        if spec is None:
            return None
        record = _records(document)
        if record is None:
            return None
        if record["entity"][0].casefold() != spec.entity:
            return None
        field = record.get(spec.field)
        if field is None:
            return None
        value, start, end = field
        citation = EvidenceCitation.from_document(document, start, end)
        return EvidenceClaim(
            text=value, citation=citation,
            method="structured_literal", entity=spec.entity, field=spec.field,
        )


class LocalExtractiveReader:
    """Optional real MiniLM QA reader. Loads local safetensors, CPU only.

    A copied span is not semantic verification: the decision policy must
    return REVIEW, never ANSWER, for this reader without another verifier.
    """

    name = "local_extractive_unverified"

    def __init__(self, model_directory: str, *, null_threshold: float = 0.0) -> None:
        import torch
        from transformers import AutoModelForQuestionAnswering, AutoTokenizer

        if null_threshold < 0:
            raise ValueError("Null threshold must be nonnegative")
        self.threshold = null_threshold
        self.tokenizer = AutoTokenizer.from_pretrained(
            model_directory, local_files_only=True, use_fast=True
        )
        if not self.tokenizer.is_fast:
            raise ValueError("Exact tokenizer offsets require a fast tokenizer")
        self.model = AutoModelForQuestionAnswering.from_pretrained(
            model_directory, local_files_only=True, use_safetensors=True
        ).to("cpu")
        self.model.eval()

    def extract(
        self, question: str, document: Document, spec: QuestionSpec | None
    ) -> EvidenceClaim | None:
        import torch
        from raglab.micro.extractive_reader import decode_qa_span

        batch = self.tokenizer(
            question, document.text,
            truncation="only_second", max_length=384,
            return_offsets_mapping=True, return_tensors="pt",
        )
        offsets = [
            tuple(map(int, pair))
            for pair in batch["offset_mapping"][0].tolist()
        ]
        sequence_ids = batch.sequence_ids(0)
        del batch["offset_mapping"]
        ids = batch["input_ids"][0]
        positions = (ids == self.tokenizer.cls_token_id).nonzero()
        if positions.numel() == 0:
            raise ValueError("Reader tokenizer lacks CLS token")
        with torch.inference_mode():
            outputs = self.model(**batch)
        pred = decode_qa_span(
            context=document.text, offsets=offsets, sequence_ids=sequence_ids,
            start_logits=outputs.start_logits[0].tolist(),
            end_logits=outputs.end_logits[0].tolist(),
            cls_index=int(positions[0].item()),
            threshold=self.threshold,
        )
        if not pred.answered or pred.start is None or pred.end is None:
            return None
        return EvidenceClaim(
            pred.text,
            EvidenceCitation.from_document(document, pred.start, pred.end),
            method="extractive_unverified",
            entity=spec.entity if spec else None,
            field=spec.field if spec else None,
            margin=pred.logit_margin,
        )
