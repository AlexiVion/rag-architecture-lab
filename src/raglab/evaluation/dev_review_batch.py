from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from collections.abc import Callable
from copy import deepcopy
from pathlib import Path
from typing import Any

from raglab.evaluation.interactive_review import annotate_packet
from raglab.evaluation.semantic_review import summarize_review_packet

Ask = Callable[[str], str]
Show = Callable[[str], Any]
CASE_PATTERN = re.compile(
    r"DEV\d{3}_(qrel_relevant_candidate|cross_query_alternate_candidate|no_context_control)"
)


def _load_suite(suite: Path) -> dict[str, Any]:
    payload = json.loads((suite / "manifest.json").read_text(encoding="utf-8"))
    if (
        payload.get("schema_version") != 1
        or payload.get("experiment_id") != "M2-DEV-EVIDENCE-01"
        or payload.get("dataset") != "beir/scifact/train"
    ):
        raise ValueError("Only M2 TRAIN evidence suites may be reviewed")
    cases = payload.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("Suite manifest has no cases")
    seen = set()
    for case in cases:
        if not isinstance(case, dict):
            raise ValueError("Malformed case in manifest")
        cid = case.get("case_id")
        if not isinstance(cid, str) or CASE_PATTERN.fullmatch(cid) is None:
            raise ValueError(f"Unsafe or unknown case id: {cid}")
        if cid in seen:
            raise ValueError("Duplicate case ID")
        seen.add(cid)
        if case.get("review_packet_filename") != cid + ".json":
            raise ValueError("Case filename does not match its validated ID")
    return payload


def _blind_id(manifest: dict[str, Any], case_id: str) -> str:
    # Stable within an immutable corpus/seed. Blind naming avoids exposing arms.
    signature = (
        f"{manifest['corpus_fingerprint']}|{manifest['seed']}|{case_id}"
    ).encode("utf-8")
    return hashlib.sha256(signature).hexdigest()[:16]


def _annotation_path(suite: Path, manifest: dict[str, Any], case_id: str) -> Path:
    return suite / "human-reviews" / ("blind_" + _blind_id(manifest, case_id) + ".json")


def _validate_annotation(
    path: Path,
    *,
    manifest: dict[str, Any],
    case: dict[str, Any],
) -> str:
    review = json.loads(path.read_text(encoding="utf-8"))
    provenance = review.get("provenance", {})
    if not isinstance(provenance, dict):
        raise ValueError(f"Invalid review provenance: {path}")
    if provenance.get("dataset") != "beir/scifact/train":
        raise ValueError(f"Review is not SciFact TRAIN: {path}")
    if provenance.get("blind_case_id") != _blind_id(manifest, case["case_id"]):
        raise ValueError(f"Review blind ID mismatch: {path}")
    if provenance.get("case_id") or provenance.get("review_arm"):
        raise ValueError("Review is not blinded")
    srcs = review.get("sources")
    ids = [str(x.get("doc_id")) for x in srcs] if isinstance(srcs, list) else None
    if ids != case.get("source_doc_ids"):
        raise ValueError("Reviewed source IDs differ from manifest")
    result = summarize_review_packet(review)
    return str(result["review_status"])


def review_next_dev_group(
    suite: Path,
    *,
    max_cases: int = 3,
    ask: Ask = input,
    show: Show = print,
) -> dict[str, Any]:
    """Review the next question group with blind arm labels; save each case.

    Completed reviews remain immutable. Interrupted runs resume from the
    first not-yet-annotated packet. Incomplete saves remain saved and visible;
    they are not silently counted as finished.
    """
    if not (1 <= max_cases <= 18):
        raise ValueError("max_cases must be between 1 and 18")
    manifest = _load_suite(suite)
    cases = manifest["cases"]
    annotated: dict[str, str] = {}
    for case in cases:
        destination = _annotation_path(suite, manifest, case["case_id"])
        if destination.exists():
            annotated[case["case_id"]] = _validate_annotation(
                destination, manifest=manifest, case=case
            )
    pending = [c for c in cases if c["case_id"] not in annotated]
    if not pending:
        return {
            "reviewed_total": len(annotated),
            "complete_total": sum(x == "complete" for x in annotated.values()),
            "pending_total": 0,
            "newly_saved": 0,
            "message": "No unreviewed packets remain. Check incomplete reviews separately.",
        }

    # A session handles one scientific proposition (up to 3 evidence
    # scenarios), but conceals which source came from the qrel/alternate arm.
    first_query_id = pending[0]["query_id"]
    group = [c for c in pending if c["query_id"] == first_query_id]
    group.sort(key=lambda c: _blind_id(manifest, c["case_id"]))
    chosen = group[:max_cases]

    review_dir = suite / "human-reviews"
    review_dir.mkdir(parents=True, exist_ok=True)
    show("=== M2 TRAIN | revisión ciega de contextos ===")
    show(f"Casos pendientes: {len(pending)} de {len(cases)}.")
    show(f"Esta sesión contiene {len(chosen)} casos de una misma proposición.")
    show("NO se muestra si la fuente proviene de qrels o de otra pregunta.")
    show("Cuando no puedas evaluar un artículo científico, elegí 'u' (incierto).")
    show("Cada revisión se guarda por separado para permitir continuar más adelante.")

    saved = 0
    for position, case in enumerate(chosen, start=1):
        source_path = suite / case["review_packet_filename"]
        packet = json.loads(source_path.read_text(encoding="utf-8"))
        provenance = packet.get("provenance")
        if not isinstance(provenance, dict):
            raise ValueError("Invalid input packet provenance")
        if provenance.get("dataset") != "beir/scifact/train":
            raise ValueError("Input packet is not SciFact TRAIN")
        if provenance.get("case_id") != case["case_id"]:
            raise ValueError("Input packet/manifest case mismatch")
        packet = deepcopy(packet)
        packet["provenance"].pop("review_arm", None)
        packet["provenance"].pop("case_id", None)
        packet["provenance"]["blind_case_id"] = _blind_id(manifest, case["case_id"])
        show(f"\n--- Caso {position}/{len(chosen)} (origen oculto) ---")
        result = annotate_packet(packet, ask=ask, show=show)
        summarize_review_packet(result)  # Validate labels before writing.
        path = _annotation_path(suite, manifest, case["case_id"])
        with path.open("x", encoding="utf-8") as stream:
            json.dump(result, stream, indent=2, ensure_ascii=False)
        saved += 1
        show("Caso guardado en la carpeta local human-reviews.")
    # Reload statuses so incomplete submissions are not conflated with a
    # complete human label.
    statuses = []
    for case in cases:
        output = _annotation_path(suite, manifest, case["case_id"])
        if output.exists():
            statuses.append(_validate_annotation(output, manifest=manifest, case=case))
    return {
        "reviewed_total": len(statuses),
        "complete_total": sum(x == "complete" for x in statuses),
        "incomplete_total": sum(x != "complete" for x in statuses),
        "pending_total": len(cases) - len(statuses),
        "newly_saved": saved,
        "review_directory": str(review_dir),
        "note": "Only human source labels/expected behavior; no generation or training.",
    }
