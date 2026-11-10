"""ConfRAG development-only *viewpoint cluster* controls.

ConfRAG's multiple answer clusters are distinct perspectives, NOT necessarily
logical contradictions. This module NEVER converts cluster disagreement into
a ground-truth entailment or contradiction label. Published source labels are
not independent two-reviewer human labels; no model is trained here.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from itertools import combinations
from typing import Any

_TOKEN = re.compile(r"[a-z0-9]+", flags=re.I)


def extract_viewpoint_pairs(record: dict[str, Any], *, max_websites: int = 6) -> list[dict]:
    """Build document-grouped pairs using *unambiguous* public cluster membership.

    Each usable website's extracted answer must have exactly one gold viewpoint
    cluster. Ambiguous, empty, duplicate and oversized entries are excluded.
    Website content is NOT inspected by this author-oracle diagnostic.
    """
    if not 2 <= max_websites <= 10:
        raise ValueError("Bounded website count must be 2..10")
    if not isinstance(record, dict):
        raise ValueError("Expected a ConfRAG record")
    group_id = record.get("id")
    question = record.get("question")
    if not isinstance(group_id, int) or not isinstance(question, str) or not 5 <= len(question) <= 350:
        return []
    members: dict[int, set[int]] = defaultdict(set)
    for cluster_no, cluster in enumerate(record.get("answers", [])):
        if not isinstance(cluster, dict):
            continue
        for idx in cluster.get("index", []):
            if isinstance(idx, int) and idx > 0:
                members[idx].add(cluster_no)
    websites = record.get("websites", [])
    if not isinstance(websites, list):
        return []
    claims: dict[int, tuple[str, int]] = {}
    for web in websites:
        if not isinstance(web, dict):
            continue
        idx, answer = web.get("index"), web.get("answer")
        if (not isinstance(idx, int) or len(members[idx]) != 1
                or not isinstance(answer, str) or not 4 <= len(answer.strip()) <= 500):
            continue
        if idx in claims:
            # Duplicate index cannot be linked to a unique original source.
            claims.pop(idx)
            members[idx].add(-1)
            continue
        claims[idx] = (answer.strip(), next(iter(members[idx])))
    chosen = sorted(claims.items())[:max_websites]
    pairs = []
    for (left_idx, (left, left_cluster)), (right_idx, (right, right_cluster)) in combinations(chosen, 2):
        pairs.append({
            "pair_id": f"{group_id}:{left_idx}-{right_idx}",
            "group_id": str(group_id),
            "contradicts_question_flag": record.get("contradicts") is True,
            "left_source_index": left_idx,
            "right_source_index": right_idx,
            "same_annotated_viewpoint": left_cluster == right_cluster,
            "left": f"Question: {question}\nAnswer: {left}",
            "right": f"Question: {question}\nAnswer: {right}",
        })
    return pairs


def lexical_viewpoint_different(left: str, right: str, *, cutoff: float = 0.5) -> bool:
    """Fixed non-neural control, not a fitted classifier."""
    # Strip identical question prefixes; otherwise every pair looks similar.
    a = left.split("\nAnswer: ", 1)[-1]
    b = right.split("\nAnswer: ", 1)[-1]
    ta, tb = set(_TOKEN.findall(a.casefold())), set(_TOKEN.findall(b.casefold()))
    if not ta or not tb:
        return True
    return len(ta & tb) / len(ta | tb) < cutoff


def binary_viewpoint_score(rows: list[dict], prediction_key: str) -> dict[str, Any]:
    """Agreement with ConfRAG answer-cluster *difference*, NOT contradiction."""
    if not rows:
        raise ValueError("No eligible pairs")
    if len({row["pair_id"] for row in rows}) != len(rows):
        raise ValueError("Duplicate pair IDs")
    counts = {"tp": 0, "tn": 0, "fp": 0, "fn": 0}
    groups: set[str] = set()
    for row in rows:
        if not isinstance(row[prediction_key], bool):
            raise ValueError("Binary verdicts must be boolean")
        expected = not row["same_annotated_viewpoint"]
        pred = row[prediction_key]
        groups.add(row["group_id"])
        key = "tp" if pred and expected else "tn" if not pred and not expected else "fp" if pred else "fn"
        counts[key] += 1
    tp, tn, fp, fn = (counts[key] for key in ("tp", "tn", "fp", "fn"))
    pos, neg = tp + fn, tn + fp
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / pos if pos else None
    f1 = 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else None
    return {
        "unit": "author_annotated_viewpoint_cluster_difference_not_factual_contradiction",
        "n_pairs": len(rows), "n_source_question_groups": len(groups),
        "counts": counts, "accuracy": (tp + tn) / len(rows),
        "different_viewpoint_precision": precision,
        "different_viewpoint_recall": recall,
        "different_viewpoint_f1": f1,
        "balanced_accuracy": (
            (tp / pos + tn / neg) / 2 if pos and neg else None
        ),
    }


def fingerprints(rows: list[dict]) -> dict[str, Any]:
    """Deterministic hashes of selected *inputs*, no copyrighted text stored."""
    pairs = sorted(rows, key=lambda row: row["pair_id"])
    if not pairs:
        raise ValueError("Cannot fingerprint empty inputs")
    digests = {
        r["pair_id"]: hashlib.sha256(
            json.dumps(
                {k: r[k] for k in (
                    "pair_id", "group_id", "same_annotated_viewpoint", "left", "right"
                )}, sort_keys=True, ensure_ascii=False
            ).encode("utf-8")
        ).hexdigest()
        for r in pairs
    }
    overall = hashlib.sha256(
        json.dumps(digests, sort_keys=True).encode("utf-8")
    ).hexdigest()
    return {"selected_pairs_sha256": overall, "pair_sha256": digests}
