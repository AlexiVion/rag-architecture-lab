"""Transparent automatic SQuAD reference QA metrics; NOT semantic source support.

Based on SQuAD token normalisation (lowercase, punctuation/articles removal).
These scores compare short predicted strings against official references, not
their citations, provenance, entailment, safety, or independent human judgments.
"""

from __future__ import annotations

import math
import random
import re
import string
from collections import Counter, defaultdict
from statistics import mean
from typing import Any, Mapping, Sequence

from raglab.micro.squad_benchmark import NaturalQABenchmark

_ARTICLES = re.compile(r"\b(a|an|the)\b", re.UNICODE)
_CITE = re.compile(r"\[(?:S[1-9]\d*)\]")
_ABSTAIN = frozenset(
    (
        "",
        "insufficient_evidence",
        "the available evidence is insufficient",
        "the available retrieved evidence is insufficient to answer",
        "no source passage matched the lexical evidence selector",
    )
)


def _clean_answer(text: str) -> str:
    text = _CITE.sub("", text)
    return text.strip().strip('"').strip()


def is_abstention(text: str, status: str = "") -> bool:
    if status == "abstained_no_evidence":
        return True
    cleaned = _clean_answer(text).strip().rstrip(".").casefold()
    return cleaned in _ABSTAIN


def normalize_answer(text: str) -> str:
    text = _clean_answer(text).lower()
    text = "".join(ch for ch in text if ch not in string.punctuation)
    text = _ARTICLES.sub(" ", text)
    return " ".join(text.split())


def _token_f1(predicted: str, gold: str) -> float:
    pred_tokens = normalize_answer(predicted).split()
    gold_tokens = normalize_answer(gold).split()
    if not pred_tokens or not gold_tokens:
        return float(pred_tokens == gold_tokens)
    common = sum((Counter(pred_tokens) & Counter(gold_tokens)).values())
    if not common:
        return 0.0
    precision = common / len(pred_tokens)
    recall = common / len(gold_tokens)
    return 2 * precision * recall / (precision + recall)


def score_prediction(
    generated: str | None,
    answers: Sequence[str],
    *,
    generation_status: str,
) -> dict[str, Any]:
    if generated is None:
        return {
            "reference_em": None, "reference_f1": None,
            "abstained": None, "is_scored": False,
        }
    abstained = is_abstention(generated, generation_status)
    if not answers:
        value = float(abstained)
        return {
            "reference_em": value,
            "reference_f1": value,
            "abstained": abstained,
            "is_scored": True,
        }
    if abstained:
        return {
            "reference_em": 0.0, "reference_f1": 0.0,
            "abstained": True, "is_scored": True,
        }
    return {
        "reference_em": float(
            any(normalize_answer(generated) == normalize_answer(a) for a in answers)
        ),
        "reference_f1": max(_token_f1(generated, a) for a in answers),
        "abstained": False,
        "is_scored": True,
    }


def _percentile(numbers: list[float], p: float) -> float | None:
    if not numbers:
        return None
    values = sorted(numbers)
    index = (len(values) - 1) * p
    left, right = math.floor(index), math.ceil(index)
    return values[left] + (values[right] - values[left]) * (index - left)


def evaluate_squad_traces(
    benchmark: NaturalQABenchmark,
    result: Mapping[str, Any],
) -> dict:
    if result.get("dataset", {}).get("sha256") != benchmark.dataset.fingerprint:
        raise ValueError("Benchmark source and trace dataset fingerprints differ")
    if result.get("scientific_validation") != "NOT_RUN":
        raise ValueError("Only raw unverified experiment traces can be scored here")
    seen: set[tuple[str, str]] = set()
    by_mode: dict[str, list[dict]] = defaultdict(list)
    detail = []
    for row in result["cases"]:
        case_id = str(row["case_id"])
        mode = str(row["mode"])
        if case_id not in benchmark.references or (case_id, mode) in seen:
            raise ValueError("Unexpected/duplicate case and mode in trace")
        seen.add((case_id, mode))
        ref = benchmark.references[case_id]
        gen_status = str(row["generation_status"])
        metric = score_prediction(row["generation"], ref.answers, generation_status=gen_status)
        quoted = [
            s["quote"] for s in row["context"]["spans"]
            if s["doc_id"] == ref.gold_doc_id
        ]
        gold_answer_literal_present = (
            any(any(answer in quote for answer in ref.answers) for quote in quoted)
            if ref.answerable else None
        )
        is_gold_in_retrieved_ids = ref.gold_doc_id in row["retrieved_ids"]
        scored = {
            "case_id": case_id,
            "article_group": ref.official_title,
            "mode": mode,
            "answerable": ref.answerable,
            "reference_em": metric["reference_em"],
            "reference_f1": metric["reference_f1"],
            "abstained": metric["abstained"],
            "is_scored": metric["is_scored"],
            "gold_doc_in_retrieved_ids": is_gold_in_retrieved_ids,
            "literal_gold_answer_in_context": gold_answer_literal_present,
            "context_tokens": row["context"]["used_tokens"],
            "prompt_content_tokens": row["prompt_content_tokens"],
            "timing_ms": row["timing_ms"],
            "generation_status": gen_status,
        }
        detail.append(scored)
        by_mode[mode].append(scored)

    if len(seen) != len(benchmark.dataset.cases) * len(result["config"]["modes"]):
        raise ValueError("Incomplete mode-by-case matrix")
    summaries = {}
    for mode, rows in sorted(by_mode.items()):
        answered = [x for x in rows if x["is_scored"]]
        positives = [x for x in answered if x["answerable"]]
        negatives = [x for x in answered if not x["answerable"]]
        retrieval_positives = [
            x for x in rows if x["answerable"] and mode not in {"no_retrieval", "oracle"}
        ]
        summaries[mode] = {
            "n_total": len(rows),
            "n_generated_or_deterministic": len(answered),
            "n_answerable_scored": len(positives),
            "n_unanswerable_scored": len(negatives),
            "reference_em": mean([x["reference_em"] for x in answered]) if answered else None,
            "reference_f1": mean([x["reference_f1"] for x in answered]) if answered else None,
            "answerable_em": mean([x["reference_em"] for x in positives]) if positives else None,
            "unanswerable_refusal_accuracy": mean(
                [x["reference_em"] for x in negatives]
            ) if negatives else None,
            "false_abstention_rate_on_answerable": mean(
                [float(x["abstained"]) for x in positives]
            ) if positives else None,
            "gold_doc_recall_at_k": mean(
                [float(x["gold_doc_in_retrieved_ids"]) for x in retrieval_positives]
            ) if retrieval_positives else None,
            "gold_literal_answer_coverage_answerable": (
                mean([float(x["literal_gold_answer_in_context"]) for x in positives])
                if positives and mode != "no_retrieval" else None
            ),
            "mean_evidence_tokens": mean([x["context_tokens"] for x in rows]),
            "p50_generation_ms": _percentile(
                [x["timing_ms"]["generation"] for x in answered], 0.5
            ),
            "p95_generation_ms": _percentile(
                [x["timing_ms"]["generation"] for x in answered], 0.95
            ),
            "p95_trace_total_ms": _percentile(
                [x["timing_ms"]["total"] for x in answered], 0.95
            ),
        }
    bootstrap = paired_group_bootstrap(detail)
    return {
        "schema_version": 1,
        "status": "PUBLIC_DEV_REFERENCE_METRICS_NOT_SEMANTIC_VALIDATION",
        "paired_article_bootstrap": bootstrap,
        "data": benchmark.manifest(),
        "candidate": result["candidate"],
        "experiment_config": result["config"],
        "by_mode": summaries,
        "cases": detail,
        "limitations": [
            "SQuAD v2 reference exact-match/F1 is NOT semantic support or hallucination detection",
            "Unanswerable judged by strict refusal string; other refusals may be missed",
            "Question groups balanced 50/50 answerability; not full-dataset prevalence",
            "Public DEV may have appeared in model pretraining or tuning",
            "Short generated answers may include prompt echoes or extraneous citation text",
            "Small pilot does not support statistical superiority, reliability or p95 generalization",
            "Retrieval scores and answer reference metrics are different outcomes",
            "Oracle gold context excluded from deployable model comparisons",
            "SQuAD unanswerability is relative to the original single paragraph, NOT necessarily the entire retrieved multi-document corpus",
            "Article-group bootstrap describes DEV uncertainty only, not pretraining-independent generalization",
            "Cross-model training, size and instructions differ; compare systems not model superiority",
        ],
    }


def paired_group_bootstrap(rows: Sequence[dict], *, iterations: int = 1000) -> dict:
    """Paired CI resampling *articles*, not correlated questions independently.

    CIs are suppressed with fewer than 10 distinct article groups. Published DEV
    contamination limits all generalization inferences even when CI is nonzero.
    """
    if iterations < 100:
        raise ValueError("At least 100 bootstrap replicates required")
    by_mode_case = {(r["mode"], r["case_id"]): r for r in rows}
    comparisons = (
        ("naive", "spans"),
        ("naive_compact", "spans_compact"),
        ("naive", "naive_compact"),
        ("spans", "spans_compact"),
    )
    result: dict[str, dict] = {}
    for base_mode, candidate_mode in comparisons:
        base = {case for mode, case in by_mode_case if mode == base_mode}
        candidate = {case for mode, case in by_mode_case if mode == candidate_mode}
        if not base or base != candidate:
            continue
        paired = [
            (
                by_mode_case[(candidate_mode, case)]["article_group"],
                by_mode_case[(candidate_mode, case)]["reference_f1"]
                - by_mode_case[(base_mode, case)]["reference_f1"],
            )
            for case in sorted(base)
            if by_mode_case[(candidate_mode, case)]["is_scored"]
            and by_mode_case[(base_mode, case)]["is_scored"]
        ]
        groups: dict[str, list[float]] = defaultdict(list)
        for group, delta in paired:
            groups[group].append(delta)
        names = sorted(groups)
        key = f"{base_mode}_to_{candidate_mode}"
        if len(names) < 10:
            result[key] = {
                "status": "INSUFFICIENT_ARTICLE_GROUPS",
                "paired_questions": len(paired),
                "distinct_articles": len(names),
                "minimum_articles": 10,
            }
            continue
        rng = random.Random(20261109)
        values = [delta for _, delta in paired]
        replicates = []
        for _ in range(iterations):
            sampled = [rng.choice(names) for _ in names]
            deltas = [d for title in sampled for d in groups[title]]
            replicates.append(mean(deltas))
        result[key] = {
            "status": "EXPLORATORY_DEV_ARTICLE_BOOTSTRAP",
            "paired_questions": len(paired),
            "distinct_articles": len(names),
            "reference_f1_delta": mean(values),
            "percentile_ci95": [
                _percentile(replicates, 0.025),
                _percentile(replicates, 0.975),
            ],
            "seed": 20261109,
            "iterations": iterations,
            "limitations": "Public DEV, possibly pretrained; interval is descriptive only",
        }
    return result
