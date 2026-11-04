from __future__ import annotations

import re
from collections import Counter
from collections.abc import Mapping
from typing import Any

from raglab.citations import validate_citations

_CITATION_RE = re.compile(r"\[(S\d+)\]")
_SENTENCES_RE = re.compile(r"(?<=[.!?])\s+|\n+")

SOURCE_LABELS = {"unreviewed", "relevant", "partially_relevant", "irrelevant", "uncertain"}
CLAIM_LABELS = {"unreviewed", "supported", "contradicted", "unsupported", "uncertain"}
BEHAVIOR_LABELS = {"unreviewed", "answer", "abstain", "uncertain"}


def prepare_review_packet(artifact: Mapping[str, Any]) -> dict[str, Any]:
    """Make a no-model, *unlabelled* human-review worksheet from a V2 JSON.

    Neither test qrels nor model guesses are used to assign semantic labels.
    Source text is taken from the exact passages passed to the generator.
    """
    result = artifact.get("result")
    if not isinstance(result, dict):
        raise ValueError("Expected a V2 result object")
    sources = result.get("sources")
    if not isinstance(sources, list) or not all(isinstance(s, dict) for s in sources):
        raise ValueError("Expected a list of source objects")
    labels = [str(s.get("label", "")) for s in sources]
    if len(set(labels)) != len(labels) or any(not re.fullmatch(r"S\d+", x) for x in labels):
        raise ValueError("Invalid or duplicate source labels")

    status = str(result.get("output_status", "unknown_legacy"))
    rejected = status == "rejected_citation_contract"
    raw = result.get("raw_generation")
    if rejected:
        if not isinstance(raw, str):
            raise ValueError("A rejected generation must include raw_generation")
        generated_text = raw
    elif bool(result.get("abstained", False)):
        generated_text = ""
    else:
        generated_text = result.get("answer")
        if not isinstance(generated_text, str):
            raise ValueError("Missing answer text")

    clauses = [
        s.strip()
        for s in _SENTENCES_RE.split(generated_text)
        if s.strip() and any(c.isalpha() for c in s)
    ]
    cite_report = validate_citations(generated_text, labels)

    return {
        "schema_version": 1,
        "provenance": {
            "artifact_filename": None,
            "artifact_sha256": None,
            "dataset": artifact.get("dataset"),
            "query_id": artifact.get("query_id"),
            "retrieval_name": result.get("retrieval_name"),
            "generator_name": result.get("generator_name"),
            "output_status": status,
        },
        "question": result.get("question"),
        "candidate_text": generated_text,
        "citation_gate": {
            "passed": cite_report.citation_contract_passed,
            "count": cite_report.citation_count,
            "invalid_labels": list(cite_report.invalid_labels),
            "coverage": cite_report.sentence_coverage,
            "note": "This is syntax and citation coverage only, not semantic support.",
        },
        "sources": [
            {
                "label": str(s["label"]),
                "doc_id": str(s.get("doc_id", "")),
                "title": str(s.get("title", "")),
                "text": str(s.get("text", "")),
                "relevance": "unreviewed",
                "relevance_notes": "",
            }
            for s in sources
        ],
        "claims": [
            {
                "claim_id": i,
                "text": clause,
                "citation_labels": list(dict.fromkeys(_CITATION_RE.findall(clause))),
                "support": "unreviewed",
                "reviewed_evidence_labels": [],
                "notes": "",
            }
            for i, clause in enumerate(clauses, start=1)
        ],
        "review": {
            "reviewer": "",
            "expected_behavior": "unreviewed",
            "notes": "",
        },
        "instructions": [
            "Do not assume a valid citation means support or that a qrel implies truth.",
            "Independently label each source's relevance to the question.",
            "For each generated claim, judge whether the cited evidence supports, contradicts or fails to support it.",
            "For supported/contradicted claims record reviewed_evidence_labels pointing to source labels.",
            "Specify expected_behavior (answer/abstain/uncertain) and reviewer before scoring a complete review.",
            "SciFact benchmark inputs are often propositions requiring verification, not ordinary questions.",
            "Review all source snippets as supplied. They may be truncated; request original article when unclear.",
        ],
    }


def summarize_review_packet(packet: Mapping[str, Any]) -> dict[str, Any]:
    """Score *explicitly supplied* human labels; never infer semantic support."""
    if packet.get("schema_version") != 1:
        raise ValueError("Unsupported semantic review schema version")
    sources = packet.get("sources")
    claims = packet.get("claims")
    review = packet.get("review")
    if not isinstance(sources, list) or not isinstance(claims, list) or not isinstance(review, dict):
        raise ValueError("Invalid semantic review packet shape")

    source_labels: list[str] = []
    relevance_counts: Counter[str] = Counter()
    for src in sources:
        if not isinstance(src, dict):
            raise ValueError("Malformed source")
        label = str(src.get("label", ""))
        if not re.fullmatch(r"S\d+", label) or label in source_labels:
            raise ValueError("Invalid or duplicate source label")
        source_labels.append(label)
        relev = src.get("relevance", "unreviewed")
        if relev not in SOURCE_LABELS:
            raise ValueError(f"Invalid source relevance: {relev}")
        relevance_counts[relev] += 1

    support_counts: Counter[str] = Counter()
    seen_ids: set[int] = set()
    for claim in claims:
        if not isinstance(claim, dict):
            raise ValueError("Malformed claim")
        claim_id = claim.get("claim_id")
        if not isinstance(claim_id, int) or claim_id in seen_ids:
            raise ValueError("Invalid or duplicate claim ID")
        seen_ids.add(claim_id)
        support = claim.get("support", "unreviewed")
        if support not in CLAIM_LABELS:
            raise ValueError(f"Invalid support verdict: {support}")
        evidence = claim.get("reviewed_evidence_labels", [])
        if not isinstance(evidence, list) or len(set(evidence)) != len(evidence):
            raise ValueError(f"Invalid evidence labels at claim {claim_id}")
        if any(e not in source_labels for e in evidence):
            raise ValueError(f"Unknown cited evidence label at claim {claim_id}")
        if support in ("supported", "contradicted") and not evidence:
            raise ValueError(f"Supported/contradicted claim {claim_id} needs reviewed evidence")
        support_counts[support] += 1

    expected = review.get("expected_behavior", "unreviewed")
    if expected not in BEHAVIOR_LABELS:
        raise ValueError("Invalid expected behavior")
    reviewer = review.get("reviewer", "")
    if not isinstance(reviewer, str):
        raise ValueError("Reviewer must be a string")

    complete = (
        bool(reviewer.strip())
        and expected != "unreviewed"
        and relevance_counts["unreviewed"] == 0
        and support_counts["unreviewed"] == 0
    )
    citation_gate = packet.get("citation_gate")
    if not isinstance(citation_gate, dict) or not isinstance(citation_gate.get("passed"), bool):
        raise ValueError("Missing independent citation gate result")

    return {
        "schema_version": 1,
        "dataset": packet.get("provenance", {}).get("dataset"),
        "query_id": packet.get("provenance", {}).get("query_id"),
        "review_status": "complete" if complete else "incomplete",
        "reviewer": reviewer,
        "expected_behavior": expected,
        "citation_contract_passed": citation_gate["passed"],
        "source_count": len(sources),
        "source_relevance_counts": {name: relevance_counts[name] for name in sorted(SOURCE_LABELS)},
        "claim_count": len(claims),
        "claim_support_counts": {name: support_counts[name] for name in sorted(CLAIM_LABELS)},
        "fully_supported_claim_rate": (
            support_counts["supported"] / len(claims)
            if complete and claims else None
        ),
        "quality_conclusion": (
            "Human-reviewed support labels; still not an automated semantic validator."
            if complete else
            "Incomplete annotations: no semantic quality score is authorized."
        ),
    }
