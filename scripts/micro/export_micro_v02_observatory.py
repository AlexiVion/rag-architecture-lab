"""Export a **real engine execution** over explicitly fictional software fixtures.

The observatory is static: it replays the source-grounded output of MicroRAG
on known invented station records. No hosted model or dynamic factual
inference is implied. No model weights, client data, or paid API.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from raglab.micro_v02.__main__ import load_documents
from raglab.micro_v02.pipeline import MicroRAG
from raglab.micro_v02.evaluation import write_json


SCENARIOS = (
    ("conflict", "Conflicting records", "What is the start year for Station Aurora?", "CONFLICT", 25),
    ("answer", "Compatible records", "What is the start year for Station Boreal?", "ANSWER", 25),
    ("insufficient", "Missing information", "What is the start year for Station Cosmos?", "INSUFFICIENT", 25),
    ("review", "Incomplete evidence sweep", "What is the start year for Station Aurora?", "REVIEW", 1),
)


def build_public_replay(document_file: Path) -> dict[str, Any]:
    documents = load_documents(str(document_file))
    sources = {doc.id: doc for doc in documents}
    cases = []
    for ident, label, question, expected, budget in SCENARIOS:
        rag = MicroRAG(documents, top_k=1, max_entity_sweep=budget)
        result = rag.answer(question)
        if result.status != expected:
            raise AssertionError(
                f"Engine behavior changed for case {ident}: {result.status} != {expected}"
            )
        if (expected == "ANSWER") != (result.answer is not None):
            raise AssertionError("Only ANSWER may publish a value")
        if expected == "CONFLICT" and len(result.citations) < 2:
            raise AssertionError("Contradiction demo requires two original sources")
        if expected == "REVIEW" and result.source_sweep_complete:
            raise AssertionError("Review demo must demonstrate incomplete source scan")
        for citation in result.citations:
            citation.validate(sources[citation.doc_id])
        cases.append({
            "id": ident,
            "label": label,
            "question": question,
            "status": result.status,
            "answer": result.answer,
            "citations": [
                {
                    "doc_id": c.doc_id,
                    "start": c.start,
                    "end": c.end,
                    "quote": c.quote,
                    "document_sha256": c.document_sha256,
                }
                for c in result.citations
            ],
            "inspected_doc_ids": list(result.inspected_doc_ids),
            "retrieved_doc_ids": list(result.retrieved_doc_ids),
            "source_sweep_complete": result.source_sweep_complete,
            "warnings": list(result.warnings),
            "read_calls": result.read_calls,
            "scan_budget": budget,
        })
    return {
        "schema_version": 1,
        "kind": "micro_v02_engine_execution_replay",
        "status": "FICTIONAL_STRUCTURED_CPU_SOFTWARE_REPLAY_NOT_LIVE_AI",
        "generated_by": "scripts/micro/export_micro_v02_observatory.py",
        "source_fixture": "examples/micro-v02/documents.json",
        "sources": [
            {
                "id": doc.id,
                "title": doc.title or doc.id,
                "text": doc.text,
                "sha256": hashlib.sha256(doc.text.encode("utf-8")).hexdigest(),
            }
            for doc in documents
        ],
        "cases": cases,
        "method": (
            "Executed MicroRAG structured-literal reader against invented "
            "records. BM25 top_k=1; source-group scan is complete except "
            "the intentionally constrained REVIEW case. Static replay only."
        ),
        "limitations": [
            "Documents are entirely fictional, created to test software invariants.",
            "This is prerecorded execution of the real Python pipeline, not interactive model inference.",
            "Answers are literal structured field values, not free-text semantic reasoning.",
            "CPU timings are omitted because they would be specific to the CI runner.",
            "No independent human-reviewed factual reliability or cross-domain support has been demonstrated.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--documents", default="examples/micro-v02/documents.json"
    )
    parser.add_argument("--output", default=None)
    parser.add_argument("--print-json", action="store_true")
    args = parser.parse_args()
    data = build_public_replay(Path(args.documents))
    if args.output is not None:
        write_json(Path(args.output), data)
    if args.print_json:
        print("MICRO_REPLAY_JSON_START")
        print(json.dumps(data, sort_keys=True, ensure_ascii=False))
        print("MICRO_REPLAY_JSON_END")
    else:
        print(json.dumps({
            "status": data["status"],
            "cases": [case["status"] for case in data["cases"]],
            "sources": len(data["sources"]),
        }, sort_keys=True))


if __name__ == "__main__":
    main()
