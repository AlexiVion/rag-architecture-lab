from __future__ import annotations

from collections.abc import Callable, Mapping
from copy import deepcopy
from typing import Any

from raglab.evaluation.semantic_review import summarize_review_packet

Ask = Callable[[str], str]
Show = Callable[[str], Any]

SOURCE_CHOICES = {
    "r": "relevant",
    "p": "partially_relevant",
    "i": "irrelevant",
    "u": "uncertain",
    "s": "unreviewed",
}
CLAIM_CHOICES = {
    "s": "supported",
    "c": "contradicted",
    "n": "unsupported",
    "u": "uncertain",
    "k": "unreviewed",
}
BEHAVIOR_CHOICES = {
    "a": "answer",
    "b": "abstain",
    "u": "uncertain",
    "s": "unreviewed",
}


def _choice(
    prompt: str,
    choices: Mapping[str, str],
    *,
    ask: Ask,
    show: Show,
) -> str:
    while True:
        value = ask(prompt).strip().lower()
        if value in choices:
            return choices[value]
        if value in choices.values():
            return value
        show("Opción no válida. Opciones: " + ", ".join(choices))


def _evidence_labels(
    available_labels: list[str],
    *,
    ask: Ask,
    show: Show,
) -> list[str]:
    allowed = set(available_labels)
    while True:
        value = ask(
            "Etiquetas de las fuentes que examinaste (ej.: S1,S2; "
            "Enter para volver a elegir el veredicto): "
        ).strip().upper()
        if not value:
            return []
        values = [part.strip() for part in value.replace(";", ",").split(",")]
        if values and len(set(values)) == len(values) and all(x in allowed for x in values):
            return values
        show("Etiquetas no válidas. Disponibles: " + ", ".join(available_labels))


def annotate_packet(
    original: Mapping[str, Any],
    *,
    ask: Ask = input,
    show: Show = print,
) -> dict[str, Any]:
    """Collect explicit reviewer labels, never infer or overwrite the input.

    Calls to ask can be replaced by deterministic answers in unit tests.
    Skipped fields remain unreviewed; the scorer must report incomplete.
    """
    packet = deepcopy(dict(original))
    # Validate the schema before taking any reviewer input.
    summarize_review_packet(packet)
    sources = packet["sources"]
    claims = packet["claims"]
    source_labels = [str(item["label"]) for item in sources]

    show("=== M2 — Revisión humana de evidencia y afirmaciones ===")
    show("Pregunta o proposición: " + str(packet.get("question", "")))
    show("Respuesta original para auditar: ")
    show(str(packet.get("candidate_text", "")) or "(No se generó ninguna respuesta)")
    show("Las citas correctas NO prueban veracidad. Usa 'incierto' si no puedes verificar.")
    dataset_id = str(packet.get("provenance", {}).get("dataset", ""))
    if dataset_id == "beir/scifact/test":
        show("SciFact TEST: diagnóstico solamente; no usar para calibración.")
    elif dataset_id == "beir/scifact/train":
        show("SciFact TRAIN: evaluación humana de desarrollo; sin etiquetas inferidas.")
    else:
        show("Evaluación humana: comprobar procedencia del conjunto de datos.")

    reviewer = ask(
        "Identificador del revisor (Enter para dejar pendiente): "
    ).strip()
    packet["review"]["reviewer"] = reviewer

    show("=== Relevancia de las fuentes respecto a la pregunta ===")
    for source in sources:
        label = str(source["label"])
        show(f"\n[{label}] Documento: {source.get('doc_id', '')}")
        show("Título: " + str(source.get("title", "")))
        show("Fragmento RECUPERADO (puede estar truncado):")
        show(str(source.get("text", "")))
        source["relevance"] = _choice(
            f"{label} relevancia [r=relevante, p=parcial, i=irrelevante, "
            "u=incierta, s=omitir]: ",
            SOURCE_CHOICES,
            ask=ask,
            show=show,
        )
        source["relevance_notes"] = ask(
            f"{label} notas opcionales (Enter si no hay): "
        ).strip()

    show("\n=== Soporte de cada afirmación generada ===")
    for claim in claims:
        show(f"\nAfirmación #{claim['claim_id']}: {claim.get('text', '')}")
        show("Citas declaradas: " + ", ".join(claim.get("citation_labels", [])))
        while True:
            support = _choice(
                "Veredicto [s=respaldada, c=contradicha, n=no respaldada, "
                "u=incierto, k=omitir]: ",
                CLAIM_CHOICES,
                ask=ask,
                show=show,
            )
            evidence: list[str] = []
            if support in ("supported", "contradicted"):
                evidence = _evidence_labels(
                    source_labels,
                    ask=ask,
                    show=show,
                )
                if not evidence:
                    show("Para respaldada/contradicha debes indicar fuentes; "
                         "elige otro veredicto si no puedes verificarlas.")
                    continue
            claim["support"] = support
            claim["reviewed_evidence_labels"] = evidence
            claim["notes"] = ask(
                "Razón o incertidumbre (opcional): "
            ).strip()
            break

    show("\n=== Comportamiento esperado ===")
    show("¿Había evidencia suficiente para responder la pregunta?")
    packet["review"]["expected_behavior"] = _choice(
        "[a=responder, b=abstenerse, u=incierto, s=omitir]: ",
        BEHAVIOR_CHOICES,
        ask=ask,
        show=show,
    )
    packet["review"]["notes"] = ask(
        "Notas finales de revisión (opcional): "
    ).strip()
    summary = summarize_review_packet(packet)
    show("Estado: " + summary["review_status"])
    return packet
