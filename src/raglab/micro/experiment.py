"""Reproducible paired *instrumentation*, not a scientific tiny-model result.

Offline runs prepare matched no-RAG, naive, span-optimized and oracle-context
inputs. A local Transformers generator is optional and requires a local path.
Each emitted model answer remains an unverified draft until independent review.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable
import json
import platform
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from raglab.core import Document, SearchResult
from raglab.retrieval import BM25Retriever

from raglab.micro.registry import get_candidate
from raglab.micro.spans import EvidencePack, pack_evidence, pack_naive, proxy_tokens


@dataclass(frozen=True, slots=True)
class MicroCase:
    case_id: str
    question: str
    group_id: str
    split: str
    oracle_doc_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class MicroDataset:
    dataset_id: str
    documents: tuple[Document, ...]
    cases: tuple[MicroCase, ...]
    fingerprint: str
    fixture_only: bool = False


def _object(value: Any, label: str) -> dict:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object")
    return value


def parse_dataset(obj: Any) -> MicroDataset:
    payload = _object(obj, "dataset")
    if payload.get("schema_version") != 1:
        raise ValueError("schema_version must be 1")
    dataset_id = str(payload.get("dataset_id", "")).strip()
    if not dataset_id:
        raise ValueError("dataset_id is required")
    documents: list[Document] = []
    ids: set[str] = set()
    for row in payload.get("documents", []):
        item = _object(row, "document")
        doc_id = str(item.get("id", "")).strip()
        body = item.get("text")
        if not doc_id or doc_id in ids or not isinstance(body, str) or not body.strip():
            raise ValueError("Each document needs a unique ID and nonempty text")
        ids.add(doc_id)
        documents.append(Document(doc_id, body, str(item.get("title", ""))))
    if not documents:
        raise ValueError("At least one document is required")

    cases: list[MicroCase] = []
    case_ids: set[str] = set()
    group_splits: dict[str, str] = {}
    oracle_splits: dict[str, str] = {}
    for row in payload.get("cases", []):
        item = _object(row, "case")
        case_id = str(item.get("id", "")).strip()
        question = str(item.get("question", "")).strip()
        group_id = str(item.get("group_id", "")).strip()
        split = str(item.get("split", "")).strip()
        if not case_id or case_id in case_ids or not question or not group_id:
            raise ValueError("Each case needs unique id, question and group_id")
        if split not in {"dev", "calibration", "holdout"}:
            raise ValueError("split must be dev, calibration or holdout")
        if group_id in group_splits and group_splits[group_id] != split:
            raise ValueError("Source/entity group leaks across evaluation splits")
        group_splits[group_id] = split
        oracle_ids = item.get("oracle_doc_ids", [])
        if not isinstance(oracle_ids, list) or any(
            not isinstance(d, str) or d not in ids for d in oracle_ids
        ):
            raise ValueError("oracle_doc_ids must list known document IDs")
        for doc_id in oracle_ids:
            if doc_id in oracle_splits and oracle_splits[doc_id] != split:
                raise ValueError("Gold evidence source leaks across evaluation splits")
            oracle_splits[doc_id] = split
        case_ids.add(case_id)
        cases.append(MicroCase(case_id, question, group_id, split, tuple(oracle_ids)))
    if not cases:
        raise ValueError("At least one case is required")
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return MicroDataset(
        dataset_id, tuple(documents), tuple(cases), digest, bool(payload.get("fixture_only", False))
    )


def read_dataset(path: str | Path) -> MicroDataset:
    return parse_dataset(json.loads(Path(path).read_text(encoding="utf-8")))


def _question_prompt(question: str, pack: EvidencePack) -> str:
    return (
        f"Question:\n{question}\n\n"
        f"Evidence:\n{pack.text if pack.text else '(none)'}\n\n"
        "If there is insufficient evidence, abstain. Cite exact evidence IDs. "
        "Never claim that a citation alone proves the answer."
    )


def _run_generation(generator: Any, prompt: str, max_new_tokens: int) -> str:
    return generator.generate(
        system_prompt=(
            "Research draft only. Ground each factual claim in supplied evidence; "
            "abstain if insufficient. This output is NOT automatically verified."
        ),
        user_prompt=prompt,
        max_new_tokens=max_new_tokens,
    )


def run_micro_suite(
    dataset: MicroDataset,
    *,
    model_id: str,
    generator: Any = None,
    modes: tuple[str, ...] = ("no_retrieval", "naive", "spans", "extractive_quote", "oracle"),
    top_k: int = 5,
    max_context_tokens: int = 128,
    max_new_tokens: int = 64,
    count_tokens: Callable[[str], int] | None = None,
) -> dict:
    """Return inspectable per-case traces; no automatic correctness score.

    Oracle mode sees gold evidence IDs and therefore must NEVER be treated as
    a deployable technique or independent benchmark candidate.
    """
    candidate = get_candidate(model_id)
    allowed = {"no_retrieval", "naive", "spans", "extractive_quote", "oracle"}
    if not modes or any(mode not in allowed for mode in modes):
        raise ValueError("modes must contain valid research modes")
    if top_k <= 0 or max_context_tokens <= 0 or max_new_tokens <= 0:
        raise ValueError("top_k and token limits must be positive")
    counter = count_tokens if count_tokens is not None else proxy_tokens
    counter_method = (
        "injected_model_tokenizer_without_chat_template"
        if count_tokens is not None else "lexical_proxy_not_model_tokenizer"
    )
    docs = {doc.id: doc for doc in dataset.documents}
    retriever = BM25Retriever()
    retriever.index(dataset.documents)
    cases = []
    for case in dataset.cases:
        if case.split == "holdout":
            # Holdout may only be run after a registered protocol and an explicit
            # independent unlock. The public smoke runner is DEV/CALIBRATION only.
            raise ValueError("Holdout blocked in micro suite: independent preregistration required")
        start = time.perf_counter()
        ranked = retriever.retrieve(case.question, top_k)
        retrieval_ms = (time.perf_counter() - start) * 1000
        for mode in modes:
            begin = time.perf_counter()
            if mode == "no_retrieval":
                pack = EvidencePack((), "", max_context_tokens, 0, counter_method)
            elif mode == "naive":
                pack = pack_naive(
                    docs, ranked, max_tokens=max_context_tokens,
                    count_tokens=counter, count_method=counter_method,
                )
            elif mode in {"spans", "extractive_quote"}:
                pack = pack_evidence(
                    case.question, docs, ranked, max_tokens=max_context_tokens,
                    count_tokens=counter, count_method=counter_method,
                )
            else:
                # Oracle is explicitly evaluation-only. No retrieval-based
                # evidence identification is credited to an oracle run.
                oracle_results = [
                    SearchResult(doc_id, 1.0, rank)
                    for rank, doc_id in enumerate(case.oracle_doc_ids, start=1)
                ]
                pack = pack_naive(
                    docs, oracle_results, max_tokens=max_context_tokens,
                    count_tokens=counter, count_method=counter_method,
                )
            packing_ms = (time.perf_counter() - begin) * 1000
            prompt = _question_prompt(case.question, pack)
            generation_ms = 0.0
            answer = None
            status = "not_generated"
            if mode == "extractive_quote":
                if pack.spans:
                    answer = f"{pack.spans[0].quote} [{pack.spans[0].label}]"
                    status = "source_quote_only_not_answer"
                else:
                    answer = "No source passage matched the lexical evidence selector."
                    status = "abstained_no_evidence"
            elif generator is not None:
                if mode != "no_retrieval" and not pack.spans:
                    answer = "The available evidence is insufficient."
                    status = "abstained_no_evidence"
                else:
                    tic = time.perf_counter()
                    answer = _run_generation(generator, prompt, max_new_tokens)
                    generation_ms = (time.perf_counter() - tic) * 1000
                    status = "draft_unverified"
            cases.append(
                {
                    "case_id": case.case_id,
                    "split": case.split,
                    "group_id": case.group_id,
                    "mode": mode,
                    "question": case.question,
                    "retrieved_ids": [r.doc_id for r in ranked],
                    "context": pack.as_dict(),
                    "prompt": prompt,
                    "prompt_proxy_tokens": proxy_tokens(prompt),
                    "prompt_content_tokens": counter(prompt),
                    "generation": answer,
                    "generation_status": status,
                    "timing_ms": {
                        "retrieval": retrieval_ms,
                        "context": packing_ms,
                        "generation": generation_ms,
                        "total": retrieval_ms + packing_ms + generation_ms,
                    },
                    "oracle_used": mode == "oracle",
                }
            )
    return {
        "schema_version": 1,
        "research_status": "exploratory_unvalidated" if generator else "prepared_no_model_run",
        "scientific_validation": "NOT_RUN",
        "experiment_family": "MICRO",
        "dataset": {
            "id": dataset.dataset_id,
            "sha256": dataset.fingerprint,
            "fixture_only": dataset.fixture_only,
            "documents": len(dataset.documents),
            "questions": len(dataset.cases),
            "splits": sorted({case.split for case in dataset.cases}),
        },
        "candidate": candidate.as_dict(),
        "config": {
            "modes": list(modes),
            "retriever": "BM25",
            "top_k": top_k,
            "max_context_tokens": max_context_tokens,
            "context_count_method": counter_method,
            "max_new_tokens": max_new_tokens,
            "generator": getattr(generator, "name", None),
        },
        "environment": {"python": platform.python_version(), "platform": platform.platform()},
        "cases": cases,
        "limitations": [
            "No model weights are loaded or downloaded in prepare-only mode",
            "Synthetic fixture does NOT imply independent scientific holdout",
            "Prompt lexical token proxy is not model tokenizer count",
            "Model weights and revisions remain unpinned until explicit audit",
            "No human-reviewed answer correctness, entailment or calibrated abstention score",
            "Extractive quote mode is source reproduction, not task correctness",
            "A tokenizer counter excludes model-specific chat wrappers/special tokens",
            "Oracle uses gold evidence IDs and is diagnostic only",
            "BM25 retrieval time is repeated across modes for fair input comparison",
            "Default mode uses BM25; hybrid comparison awaits pinned retrieval run",
        ],
    }
