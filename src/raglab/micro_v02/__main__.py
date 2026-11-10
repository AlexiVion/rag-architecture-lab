"""MICRO-RAG v0.2 CLI: bounded local evidence fixture, no external API.

Examples:
  python -m raglab.micro_v02 ask --documents examples/micro-v02/documents.json \\
      --question "What is the start year for Station Aurora?"
  python -m raglab.micro_v02 evaluate --documents examples/micro-v02/documents.json \\
      --cases examples/micro-v02/cases.json --output runs/micro-v02/evaluation.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from raglab.core import Document
from raglab.micro_v02.pipeline import MicroRAG
from raglab.micro_v02.readers import LocalExtractiveReader, StructuredFactReader
from raglab.micro_v02.verifier import LocalNLIConflictVerifier
from raglab.micro_v02.evaluation import evaluate_cases, write_json


def _load_json(path: str) -> object:
    p = Path(path)
    if not p.is_file() or p.stat().st_size > 2_000_000:
        raise ValueError("Expected an existing JSON fixture <=2MB")
    return json.loads(p.read_text(encoding="utf-8"))


def load_documents(path: str) -> list[Document]:
    obj = _load_json(path)
    if not isinstance(obj, list):
        raise ValueError("Document fixture must be an array")
    try:
        return [
            Document(
                id=item["id"], text=item["text"], title=item.get("title", "")
            )
            for item in obj
        ]
    except (KeyError, TypeError) as exc:
        raise ValueError("Malformed document fixture") from exc


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    ask = sub.add_parser("ask", help="Ask with exact source offsets")
    ev = sub.add_parser("evaluate", help="Score visible synthetic demo cases only")
    for p in (ask, ev):
        p.add_argument("--documents", required=True)
        p.add_argument("--top-k", type=int, default=3)
        p.add_argument("--max-entity-sweep", type=int, default=25)
        p.add_argument("--reader", choices=("structured", "extractive"), default="structured")
        p.add_argument("--model-directory", default=None)
        p.add_argument("--verifier-directory", default=None)
    ask.add_argument("--question", required=True)
    ask.add_argument("--output", default=None)
    ev.add_argument("--cases", required=True)
    ev.add_argument("--output", required=True)
    args = parser.parse_args()
    if args.reader == "extractive" and not args.model_directory:
        parser.error("--model-directory is required for extractive reader")
    reader = (
        StructuredFactReader() if args.reader == "structured"
        else LocalExtractiveReader(args.model_directory)
    )
    verifier = (
        LocalNLIConflictVerifier(args.verifier_directory)
        if args.verifier_directory else None
    )
    pipeline = MicroRAG(
        load_documents(args.documents), reader=reader, verifier=verifier,
        top_k=args.top_k, max_entity_sweep=args.max_entity_sweep,
    )
    if args.command == "ask":
        data = pipeline.answer(args.question).to_dict()
    else:
        rows = _load_json(args.cases)
        if not isinstance(rows, list):
            raise ValueError("Case fixture must be a JSON array")
        data = evaluate_cases(pipeline, rows)
    if args.output:
        write_json(Path(args.output), data)
    print(json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False))


if __name__ == "__main__":
    main()
