"""Conservative source-consistency arbitration, not an NLI reasoner.

Only literal structured facts with the same entity+field can reach ANSWER.
Distinct values from different sources are a conflict to report; for natural
extractive spans the best supported choice is REVIEW without independent NLI.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from raglab.micro_v02.contracts import Decision, EvidenceClaim, EvidenceCitation


@dataclass(frozen=True, slots=True)
class PolicyResult:
    status: Decision
    answer: str | None
    citations: tuple[EvidenceCitation, ...]
    warnings: tuple[str, ...]


def adjudicate(
    claims: tuple[EvidenceClaim, ...], *, source_sweep_complete: bool,
) -> PolicyResult:
    if not source_sweep_complete:
        return PolicyResult(
            "REVIEW", None, tuple(c.citation for c in claims),
            ("Source coverage exceeded scan budget; no answer may be published",),
        )
    if not claims:
        return PolicyResult("INSUFFICIENT", None, (), ("No supported answer candidate",))
    if any(c.method != "structured_literal" for c in claims):
        return PolicyResult(
            "REVIEW", None, tuple(c.citation for c in claims),
            ("Verbatim model extraction is not independent semantic verification",),
        )
    groups: dict[tuple[str | None, str | None], list[EvidenceClaim]] = defaultdict(list)
    for claim in claims:
        groups[(claim.entity, claim.field)].append(claim)
    if len(groups) != 1:
        return PolicyResult(
            "REVIEW", None, tuple(c.citation for c in claims),
            ("Candidates describe different entities or fields",),
        )
    canonical: dict[str, list[EvidenceClaim]] = defaultdict(list)
    for claim in claims:
        canonical[" ".join(claim.text.casefold().split())].append(claim)
    if len(canonical) > 1:
        # Do not silently prefer latest, highest BM25 score, or one document.
        sources = {claim.citation.doc_id for claim in claims}
        if len(sources) < 2:
            return PolicyResult(
                "REVIEW", None, tuple(c.citation for c in claims),
                ("One source reports multiple incompatible values",),
            )
        return PolicyResult(
            "CONFLICT", None, tuple(c.citation for c in claims),
            ("Different literal values for one field across distinct sources; no authority resolution",),
        )
    return PolicyResult(
        "ANSWER", claims[0].text, tuple(c.citation for c in claims), (),
    )
