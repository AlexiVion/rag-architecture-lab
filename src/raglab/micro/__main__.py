"""CLI: python -m raglab.micro {registry,prepare,score}."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from raglab.micro.evaluation import assess_human_reviews
from raglab.micro.experiment import read_dataset, run_micro_suite
from raglab.micro.registry import CANDIDATES, registry_manifest


def _write(result: dict, output: str | None) -> None:
    body = json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    if output:
        target = Path(output)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")
        print(
            json.dumps(
                {
                    "output": str(target),
                    "scientific_validation": result.get("scientific_validation", "NOT_RUN"),
                    "status": result.get("research_status", "REVIEW_ONLY"),
                }
            )
        )
    else:
        print(body)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="python -m raglab.micro",
        description="CPU-first exploratory tiny-model research (never auto-publish scores)",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    registry = sub.add_parser("registry", help="Unmeasured model candidates; no downloads")
    registry.add_argument("--output")
    prepare = sub.add_parser("prepare", help="Generate matched per-case traces")
    prepare.add_argument("--data", required=True)
    prepare.add_argument("--output", required=True)
    prepare.add_argument(
        "--model-id", choices=[candidate.key for candidate in CANDIDATES],
        default="pythia-14m",
    )
    prepare.add_argument("--backend", choices=("none", "local"), default="none")
    prepare.add_argument("--local-model-dir")
    prepare.add_argument("--modes", nargs="+", default=["no_retrieval", "naive", "spans", "oracle"])
    prepare.add_argument("--top-k", type=int, default=5)
    prepare.add_argument("--max-context-tokens", type=int, default=128)
    prepare.add_argument("--max-new-tokens", type=int, default=64)
    score = sub.add_parser("score", help="Aggregate independently reviewed labels only")
    score.add_argument("--reviews", required=True)
    score.add_argument("--output")
    args = parser.parse_args(argv)

    if args.command == "registry":
        _write(registry_manifest(), args.output)
        return
    if args.command == "score":
        reviews = json.loads(Path(args.reviews).read_text(encoding="utf-8"))
        if not isinstance(reviews, list):
            parser.error("reviews file must contain an array of reviewer judgments")
        _write(assess_human_reviews(reviews), args.output)
        return

    generator = None
    if args.backend == "local":
        if not args.local_model_dir or not Path(args.local_model_dir).is_dir():
            parser.error("--backend local requires an existing --local-model-dir")
        # No public checkpoint URL, auth token or network download at this path:
        # model loading only receives a local, operator-provided directory.
        from raglab.generation.local_transformers import LocalTransformersGenerator

        generator = LocalTransformersGenerator(str(Path(args.local_model_dir).resolve()))
    elif args.local_model_dir:
        parser.error("--local-model-dir requires --backend local")
    try:
        result = run_micro_suite(
            read_dataset(args.data),
            model_id=args.model_id,
            generator=generator,
            modes=tuple(args.modes),
            top_k=args.top_k,
            max_context_tokens=args.max_context_tokens,
            max_new_tokens=args.max_new_tokens,
        )
    except (ValueError, KeyError) as exc:
        parser.error(str(exc))
    _write(result, args.output)


if __name__ == "__main__":
    main()
