"""MICRO-CF v1: novel, deterministic, corpus-level evidence-grounding stress test.

All stations and facts are fictional and generated from a fixed seed. Every QA
label is checked against the *entire synthetic corpus partition*, not a single
SQuAD paragraph. Contradictions require refusing to claim one unique answer.

This is an ARTIFICIAL, programmatically labeled development benchmark, NOT
human-authored, a hidden external holdout, or evidence of domain generality.
The generator, templates, and audit split are publicly inspectable.
"""

from __future__ import annotations

import hashlib
import json
import random
import re
from dataclasses import dataclass
from typing import Literal

from raglab.core import Document

Kind = Literal["answer", "absent", "conflict"]
Split = Literal["dev", "calibration", "audit"]

PHASES = (
    "violet lantern", "amber cedar", "silver meadow", "teal compass",
    "indigo canyon", "copper orchard", "marble horizon", "crimson harbor",
    "ivory comet", "emerald bay", "golden summit", "coral atlas",
    "blue thistle", "pearl valley", "saffron breeze", "lilac mirror",
    "opal reef", "bronze willow", "jade meadow", "cobalt lantern",
)
SEALS = (
    "cedar triangle", "orange prism", "silver anchor", "blue willow",
    "marble feather", "violet bridge", "amber key", "green mirror",
    "pearl orbit", "copper ridge", "ivory wheel", "teal window",
    "crimson leaf", "saffron star", "indigo gate", "bronze comet",
    "opal clock", "golden river", "lilac mountain", "coral tower",
)
SYLLABLES = (
    "Vorel", "Qanix", "Mirlon", "Talven", "Cessia", "Uldan",
    "Nimara", "Sevrin", "Ordin", "Felya", "Pralen", "Yordis",
)

PRIMARY = (
    "The phase marker registered for station {name} is {phase}. "
    "The storage seal for {name} is {seal}. This is a routine inspection record.",
    "Registry note for station {name}: its phase marker reads {phase}. "
    "Its storage seal is {seal}. The routine inspection is complete.",
    "Station {name} has phase marker {phase}. A separate registry line "
    "records the storage seal as {seal}. The maintenance log is ordinary.",
    "The registry of station {name} states a phase marker of {phase} "
    "and a storage seal of {seal}. Inspection complete.",
)
OPERATIONS = (
    "Operations report for station {name}. The storage seal for {name} is {seal}. "
    "The machinery passed the routine inspection.",
    "Station {name} operations worksheet: storage seal {seal}. "
    "Only equipment condition was checked.",
    "In the operations record for station {name}, the storage seal reads {seal}. "
    "No other fields are documented.",
    "Equipment note for station {name}: the recorded storage seal is {seal}. "
    "This report does not establish document priority.",
)


def sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class CFCase:
    case_id: str
    entity: str
    split: Split
    question: str
    kind: Kind
    correct_answer: str | None
    eligible_document_ids: tuple[str, ...]
    evidence_document_ids: tuple[str, ...]

    def as_dict(self) -> dict:
        return {
            "case_id": self.case_id,
            "entity": self.entity,
            "split": self.split,
            "question": self.question,
            "kind": self.kind,
            "correct_answer": self.correct_answer,
            "eligible_document_ids": list(self.eligible_document_ids),
            "evidence_document_ids": list(self.evidence_document_ids),
        }


@dataclass(frozen=True, slots=True)
class CFPartition:
    name: Split
    documents: tuple[Document, ...]
    cases: tuple[CFCase, ...]
    sha256: str

    def as_dict(self) -> dict:
        return {
            "split": self.name, "sha256": self.sha256,
            "entity_groups": len(set(c.entity for c in self.cases)),
            "documents": len(self.documents), "cases": len(self.cases),
            "kinds": {
                k: sum(c.kind == k for c in self.cases)
                for k in ("answer", "absent", "conflict")
            },
        }


def _entity_name(i: int) -> str:
    return f"{SYLLABLES[i % len(SYLLABLES)]}-{i + 4187}"


def _manifest_payload(part: CFPartition) -> dict:
    return {
        "split": part.name,
        "documents": [
            {"id": x.id, "text": x.text, "title": x.title}
            for x in part.documents
        ],
        "cases": [x.as_dict() for x in part.cases],
    }


def build_counterfactual_corpus(seed: int = 20261109) -> dict[Split, CFPartition]:
    if seed < 0:
        raise ValueError("seed must be non-negative")
    rng = random.Random(seed)
    # Each partition gets EXACTLY 12 entities, six with two conflicting
    # storage seal values and six with two agreeing source records.
    # Every entity has three questions, including no signer in ANY document.
    ids = list(range(36))
    rng.shuffle(ids)
    partitions: dict[Split, CFPartition] = {}
    for pos, split in enumerate(("dev", "calibration", "audit")):
        chosen = ids[pos * 12:(pos + 1) * 12]
        docs: list[Document] = []
        cases: list[CFCase] = []
        phase_values = rng.sample(PHASES, 12)
        seal_values = rng.sample(SEALS, 12)
        for idx, i in enumerate(chosen):
            name = _entity_name(i)
            phase = phase_values[idx]
            seal1 = seal_values[idx]
            # Different seal if and only if one of six selected groups.
            contradictory = idx % 2 == 0
            seal2 = SEALS[(SEALS.index(seal1) + 7) % len(SEALS)] if contradictory else seal1
            a = Document(
                f"{split}-{i}-registry",
                PRIMARY[i % len(PRIMARY)].format(
                    name=name, phase=phase, seal=seal1
                ),
                f"{name} registry",
            )
            b = Document(
                f"{split}-{i}-operations",
                OPERATIONS[(i // 2) % len(OPERATIONS)].format(
                    name=name, seal=seal2
                ),
                f"{name} operations",
            )
            docs.extend((a, b))
            source_ids = (a.id, b.id)
            cases.extend((
                CFCase(
                    f"{split}-{i}-phase", name, split,
                    f"What is the phase marker of station {name}?",
                    "answer", phase, source_ids, (a.id,),
                ),
                CFCase(
                    f"{split}-{i}-seal", name, split,
                    f"What storage seal is recorded for station {name}?",
                    "conflict" if contradictory else "answer",
                    None if contradictory else seal1, source_ids, source_ids,
                ),
                CFCase(
                    f"{split}-{i}-signer", name, split,
                    f"Who signed the operating permit of station {name}?",
                    "absent", None, source_ids, (),
                ),
            ))
        # Canonical source/case order is deliberately shuffled for retrieval,
        # rather than clustering all gold docs at the start of the index.
        rng.shuffle(docs)
        rng.shuffle(cases)
        interim = CFPartition(split, tuple(docs), tuple(cases), "")
        payload = _manifest_payload(interim)
        digest = sha(json.dumps(payload, sort_keys=True, separators=(",", ":")))
        partitions[split] = CFPartition(
            split, tuple(docs), tuple(cases), digest
        )
    verify_counterfactual_corpus(partitions)
    return partitions


def verify_counterfactual_corpus(parts: dict[Split, CFPartition]) -> None:
    if set(parts) != {"dev", "calibration", "audit"}:
        raise ValueError("All three research partitions are required")
    all_ids: set[str] = set()
    all_entities: set[str] = set()
    for split, part in parts.items():
        ids = {doc.id for doc in part.documents}
        if len(ids) != 24 or len(part.cases) != 36:
            raise ValueError("Unexpected partition size")
        if ids & all_ids:
            raise ValueError("Document ID leakage between splits")
        all_ids |= ids
        groups = {c.entity for c in part.cases}
        if len(groups) != 12 or groups & all_entities:
            raise ValueError("Entity leakage between splits")
        all_entities |= groups
        by_id = {doc.id: doc for doc in part.documents}
        # No output labels are generated via a model. The assertions here
        # independently validate source coverage/contradiction invariants.
        for case in part.cases:
            if case.split != split or not set(case.eligible_document_ids) <= ids:
                raise ValueError("Cross-split corpus label leak")
            if case.kind == "answer":
                if not case.correct_answer or not all(
                    case.correct_answer in by_id[x].text
                    for x in case.evidence_document_ids
                ):
                    raise ValueError("Gold answer is missing from a required source")
            elif case.kind == "absent":
                if case.correct_answer is not None or "signed" in " ".join(
                    doc.text.lower()
                    for doc in part.documents if case.entity in doc.text
                ):
                    raise ValueError("Absent signer is not absent in full relevant corpus")
            elif case.kind == "conflict":
                if case.correct_answer is not None or len(case.evidence_document_ids) != 2:
                    raise ValueError("Incorrect conflict annotation")
                texts = [by_id[x].text.lower() for x in case.evidence_document_ids]
                # Every contradicted fact is explicitly carried in both docs.
                if not all("storage seal" in t for t in texts):
                    raise ValueError("Conflicting sources lack property statement")
            else:
                raise ValueError("Unknown case type")
        if sha(json.dumps(_manifest_payload(part), sort_keys=True, separators=(",", ":"))) != part.sha256:
            raise ValueError("Partition SHA256 drift")
    if len(all_entities) != 36 or len(all_ids) != 72:
        raise ValueError("Unexpected global corpus cardinality")


def protocol_manifest(parts: dict[Split, CFPartition]) -> dict:
    return {
        "benchmark": "MICRO-CF-v1",
        "provenance": "original deterministic invented-fiction templates and pseudonyms",
        "seed": 20261109,
        "source_license": "repository source-code license; fictional generated content",
        "labels": "programmatic corpus-relative labels, NOT independently human reviewed",
        "splits": {name: part.as_dict() for name, part in parts.items()},
        "rules": {
            "answer": "same unique value in complete relevant source group",
            "absent": "no signer disclosed for the named entity in any relevant source",
            "conflict": "two equally ranked authoritative source documents give distinct storage seals",
        },
        "limitations": [
            "Templates and artificial QA labels visible in public repository: audit is not blinded or sealed",
            "Novel fictional entities reduce memorization but do not eliminate train/test distribution leakage",
            "Synthetic, formulaic text has exploitable shortcuts and does not represent open-domain natural QA",
            "Value equality is an exact-string proxy, not full semantic entailment",
            "An evidence quote alone cannot establish human-trusted support",
        ],
    }
