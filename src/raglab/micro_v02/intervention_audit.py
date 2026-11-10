"""Paired synthetic evidence-intervention PILOT for the CPU-first MICRO-RAG study.

Inspired by (and NOT claiming to invent) Dynamic Evidence Contracts:
https://aclanthology.org/2026.emnlp-main.1494/

This instrument exercises the ZERO-neural-model structured-literal baseline.
It DOES NOT evaluate real-document semantic fidelity or validate the paper's
proposed model-size/CPU-frontier hypothesis. No independent labels are used.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from raglab.core import Document
from raglab.micro_v02.pipeline import MicroRAG

NAMES: tuple[str, ...] = (
    "Amber", "Birch", "Coral", "Dusk", "Elm", "Flint",
    "Grove", "Haven", "Ivory", "Juniper", "Kestrel", "Lumen",
)
OPERATIONS: tuple[str, ...] = (
    "baseline", "permutation", "irrelevant_addition",
    "corroboration", "direct_conflict", "support_deletion",
    "malformed_entity", "budget_exhaustion", "other_field_conflict",
)
# These expectations are visible and intentionally authored for the codebase.
# Never promote this fixture to an independent test set.
EXPECTED: dict[str, str] = {
    "baseline": "ANSWER",
    "permutation": "ANSWER",
    "irrelevant_addition": "ANSWER",
    "corroboration": "ANSWER",
    "direct_conflict": "CONFLICT",
    "support_deletion": "INSUFFICIENT",
    "malformed_entity": "REVIEW",
    "budget_exhaustion": "REVIEW",
    "other_field_conflict": "ANSWER",
}


@dataclass(frozen=True)
class InterventionCase:
    group_id: str
    condition: str
    question: str
    expected_status: str
    expected_answer: str | None
    documents: tuple[Document, ...]
    max_entity_sweep: int = 25

    @property
    def case_id(self) -> str:
        return f"{self.group_id}:{self.condition}"


def build_cases() -> tuple[InterventionCase, ...]:
    cases: list[InterventionCase] = []
    for idx, name in enumerate(NAMES):
        group = f"fictional-{idx:02d}"
        entity = f"Station {name}"
        value = str(2001 + idx)
        primary = Document(
            id=f"{group}-primary",
            title="Invented source A",
            text=f"entity: {entity}\nstart_year: {value}\nmanager: PersonA\n",
        )
        unrelated = Document(
            id=f"{group}-unrelated",
            title="Invented distractor",
            text=f"entity: Station Decoy{idx}\nstart_year: 1900\nmanager: PersonD\n",
        )
        corroboration = Document(
            id=f"{group}-corroboration",
            title="Invented matching source",
            text=f"entity: {entity}\nstart_year: {value}\nmanager: PersonA\n",
        )
        contradiction = Document(
            id=f"{group}-conflict",
            title="Invented contradictory source",
            text=f"entity: {entity}\nstart_year: {int(value) + 3}\nmanager: PersonA\n",
        )
        missing = Document(
            id=f"{group}-missing",
            title="Invented source with deleted field",
            text=f"entity: {entity}\nmanager: PersonA\n",
        )
        malformed = Document(
            id=f"{group}-malformed",
            title="Invented ambiguous duplicate entity",
            text=f"entity: {entity}\nentity: {entity}\nstart_year: {int(value) + 3}\n",
        )
        other_field = Document(
            id=f"{group}-other-field",
            title="Invented other-property disagreement",
            text=f"entity: {entity}\nstart_year: {value}\nmanager: PersonB\n",
        )
        distraction = Document(
            id=f"{group}-extra",
            title="Invented extra unrelated record",
            text=f"entity: Station Side{idx}\nstart_year: 1901\n",
        )
        configurations = {
            "baseline": (primary, unrelated),
            "permutation": (unrelated, primary),
            "irrelevant_addition": (primary, unrelated, distraction),
            "corroboration": (primary, unrelated, corroboration),
            "direct_conflict": (primary, unrelated, contradiction),
            "support_deletion": (missing, unrelated),
            "malformed_entity": (primary, unrelated, malformed),
            "budget_exhaustion": (primary, corroboration),
            "other_field_conflict": (primary, unrelated, other_field),
        }
        for operation in OPERATIONS:
            cases.append(InterventionCase(
                group_id=group,
                condition=operation,
                question=f"What is the start year for {entity}?",
                expected_status=EXPECTED[operation],
                expected_answer=value if EXPECTED[operation] == "ANSWER" else None,
                documents=configurations[operation],
                max_entity_sweep=1 if operation == "budget_exhaustion" else 25,
            ))
    return tuple(cases)


def run_pilot() -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for case in build_cases():
        # A freshly indexed corpus for each intervention: no stale retrieval
        # index or state shared across counterfactual conditions.
        result = MicroRAG(
            case.documents, top_k=1, max_entity_sweep=case.max_entity_sweep
        ).answer(case.question)
        correct = (
            result.status == case.expected_status
            and result.answer == case.expected_answer
            and (result.status != "ANSWER" or bool(result.citations))
        )
        accepted = result.status == "ANSWER"
        rows.append({
            "id": case.case_id,
            "group_id": case.group_id,
            "condition": case.condition,
            "expected_status": case.expected_status,
            "actual_status": result.status,
            "expected_answer": case.expected_answer,
            "actual_answer": result.answer,
            "compliant": correct,
            "accepted": accepted,
            "wrong_accept": accepted and not correct,
            "scan_complete": result.source_sweep_complete,
            "citations": len(result.citations),
        })
    if len({r["id"] for r in rows}) != len(rows):
        raise AssertionError("Each paired experiment must have a unique case ID")
    distributions = {
        condition: {
            "n": sum(r["condition"] == condition for r in rows),
            "compliant": sum(
                r["condition"] == condition and r["compliant"] for r in rows
            ),
        }
        for condition in OPERATIONS
    }
    accepted = [r for r in rows if r["accepted"]]
    return {
        "schema_version": 1,
        "status": "VISIBLE_AUTHOR_GENERATED_STRUCTURED_SOFTWARE_PILOT_NOT_SCIENTIFIC_EVIDENCE",
        "groups": len(NAMES),
        "conditions": list(OPERATIONS),
        "n": len(rows),
        "compliant": sum(r["compliant"] for r in rows),
        "compliance_rate": sum(r["compliant"] for r in rows) / len(rows),
        "accepted": len(accepted),
        "wrong_accepts": sum(r["wrong_accept"] for r in accepted),
        "wrong_accept_rate": (
            sum(r["wrong_accept"] for r in accepted) / len(accepted)
            if accepted else None
        ),
        "by_condition": distributions,
        "rows": rows,
        "limitations": [
            "Author-built synthetic structured-literal fixtures; labels not blinded or human reviewed.",
            "No free-text semantic inference; neither empirical generalization nor model-size novelty established.",
            "Zero wrong acceptances on these fixtures does not imply a bounded population risk.",
            "No model timing, energy, realistic corpus, paired neural control or statistical confidence bound.",
            "Intervention-based RAG evaluation is established prior art (Zeng et al., EMNLP 2026).",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=None)
    args = parser.parse_args()
    data = run_pilot()
    if args.output:
        path = Path(args.output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
                        encoding="utf-8")
    print(json.dumps({
        "status": data["status"], "n": data["n"],
        "compliant": data["compliant"], "accepted": data["accepted"],
        "wrong_accepts": data["wrong_accepts"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
