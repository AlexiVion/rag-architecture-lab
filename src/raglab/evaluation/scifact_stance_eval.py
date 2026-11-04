from __future__ import annotations

import hashlib
import io
import json
import tarfile
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from raglab.evaluation.dev_nli_pilot import DEFAULT_NLI_MODEL, NLI_LABELS, _logit_probabilities

SCIFACT_ARCHIVE_URL = "https://scifact.s3-us-west-2.amazonaws.com/release/latest/data.tar.gz"
EXPECTED_FILES = ("corpus.jsonl", "claims_train.jsonl")
LABEL_MAP = {"SUPPORT": "entailment", "CONTRADICT": "contradiction"}
MAX_DOWNLOAD_BYTES = 80_000_000
MAX_MEMBER_BYTES = 40_000_000


def ensure_official_scifact_archive(path: Path) -> Path:
    """Cache official data without shell extraction; never read the test claims."""
    if path.exists():
        if not path.is_file() or path.stat().st_size > MAX_DOWNLOAD_BYTES:
            raise ValueError("Existing SciFact archive is invalid or unexpectedly large")
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".part")
    if temporary.exists():
        raise FileExistsError("Interrupted SciFact download exists; no overwrite allowed")
    try:
        request = urllib.request.Request(
            SCIFACT_ARCHIVE_URL,
            headers={"User-Agent": "rag-architecture-lab-research/0.1"},
        )
        with urllib.request.urlopen(request, timeout=60) as connection:
            with temporary.open("xb") as output:
                total = 0
                while True:
                    chunk = connection.read(1024 * 1024)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > MAX_DOWNLOAD_BYTES:
                        raise ValueError("Official SciFact download exceeded safety budget")
                    output.write(chunk)
        # Validate the archive before making it canonical.
        read_official_train_archive(temporary)
        temporary.rename(path)
    except BaseException:
        if temporary.exists():
            temporary.unlink()
        raise
    return path


def _decode_jsonl_member(archive: tarfile.TarFile, suffix: str) -> list[dict[str, Any]]:
    matching = [
        info for info in archive.getmembers()
        if info.isfile() and (info.name == "data/" + suffix or info.name.endswith("/data/" + suffix))
    ]
    if len(matching) != 1:
        raise ValueError("Official archive missing or ambiguously contains " + suffix)
    member = matching[0]
    if member.size > MAX_MEMBER_BYTES:
        raise ValueError("Scientific corpus data member exceeds safety budget")
    stream = archive.extractfile(member)
    if stream is None:
        raise ValueError("Could not read compressed member " + suffix)
    raw = stream.read(MAX_MEMBER_BYTES + 1)
    if len(raw) > MAX_MEMBER_BYTES:
        raise ValueError("Decompressed member too large")
    rows = []
    for line in raw.decode("utf-8").splitlines():
        if line.strip():
            record = json.loads(line)
            if not isinstance(record, dict):
                raise ValueError("Malformed SciFact JSONL row")
            rows.append(record)
    if not rows:
        raise ValueError("No data rows in " + suffix)
    return rows


def read_official_train_archive(path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]], str]:
    """Only original TRAIN and corpus members; never use DEV/TEST for tuning."""
    raw = path.read_bytes()
    if len(raw) > MAX_DOWNLOAD_BYTES:
        raise ValueError("SciFact archive is too large")
    fingerprint = hashlib.sha256(raw).hexdigest()
    try:
        with tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz") as archive:
            corpus = _decode_jsonl_member(archive, "corpus.jsonl")
            claims = _decode_jsonl_member(archive, "claims_train.jsonl")
    except tarfile.TarError as exc:
        raise ValueError("Malformed official SciFact tar archive") from exc
    return corpus, claims, fingerprint


def extract_labeled_rationales(
    corpus: Iterable[dict[str, Any]],
    train_claims: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Turn expert-annotated sentence rationales into NLI premise/hypothesis pairs."""
    documents: dict[str, list[str]] = {}
    for doc in corpus:
        key = str(doc.get("doc_id", ""))
        abstract = doc.get("abstract")
        if key in documents or not key or not isinstance(abstract, list):
            raise ValueError("Malformed or duplicate SciFact corpus document")
        if not all(isinstance(x, str) for x in abstract):
            raise ValueError("SciFact corpus abstract must be a sentence list")
        documents[key] = abstract
    pairs: list[dict[str, Any]] = []
    seen: set[tuple[str, str, tuple[int, ...]]] = set()
    for claim in train_claims:
        claim_id = str(claim.get("id", ""))
        statement = claim.get("claim")
        evidence = claim.get("evidence", {})
        if not claim_id or not isinstance(statement, str) or not statement.strip():
            raise ValueError("SciFact TRAIN claim missing ID or scientific proposition")
        if not isinstance(evidence, dict):
            raise ValueError("SciFact evidence annotation is malformed")
        for doc_id, rationales in evidence.items():
            if not isinstance(rationales, list):
                raise ValueError("SciFact evidence rationale must be a list")
            sentences = documents.get(str(doc_id))
            if sentences is None:
                raise ValueError("Annotated evidence document is missing")
            for rationale in rationales:
                if not isinstance(rationale, dict):
                    raise ValueError("Malformed SciFact rationale annotation")
                gold = rationale.get("label")
                indices = rationale.get("sentences")
                if gold not in LABEL_MAP:
                    raise ValueError("Unrecognized SciFact scientific stance label")
                if not isinstance(indices, list) or not indices:
                    raise ValueError("Missing evidence sentence rationale indices")
                if any(type(i) is not int or i < 0 or i >= len(sentences) for i in indices):
                    raise ValueError("SciFact sentence rationale index out of range")
                key = (claim_id, str(doc_id), tuple(indices))
                if key in seen:
                    continue
                seen.add(key)
                premise = " ".join(sentences[index] for index in indices).strip()
                if not premise:
                    raise ValueError("Original scientific rationale is empty")
                pairs.append({
                    "claim_id": claim_id,
                    "doc_id": str(doc_id),
                    "sentence_indices": indices,
                    "premise": premise,
                    "hypothesis": statement,
                    "gold": LABEL_MAP[gold],
                })
    if not pairs:
        raise ValueError("No expert-labeled SciFact TRAIN stance pairs were found")
    return pairs


def balanced_training_sample(
    examples: list[dict[str, Any]],
    *,
    per_class: int,
    seed: int = 17,
) -> list[dict[str, Any]]:
    if per_class < 1 or per_class > 100:
        raise ValueError("per-class sample size must be between 1 and 100")
    groups = {label: [] for label in LABEL_MAP.values()}
    for example in examples:
        if example["gold"] not in groups:
            raise ValueError("Unexpected gold stance label")
        groups[example["gold"]].append(example)
    for gold in groups:
        groups[gold].sort(
            key=lambda ex: hashlib.sha256(
                (f"{seed}|{ex['claim_id']}|{ex['doc_id']}|"
                 + ",".join(map(str, ex["sentence_indices"]))).encode("utf-8")
            ).hexdigest()
        )
        if len(groups[gold]) < per_class:
            raise ValueError(f"Not enough original TRAIN {gold} examples for balanced evaluation")
    selected = groups["entailment"][:per_class] + groups["contradiction"][:per_class]
    # Strictly deterministic but interleave the two classes for inference.
    return [
        selected[i] if i % 2 == 0 else selected[per_class + i // 2]
        for i in range(2 * per_class)
    ]


def evaluate_gold_stance(
    examples: list[dict[str, Any]],
    model_logits: Any,
    *,
    archive_sha256: str,
    model_revision: str | None,
) -> dict[str, Any]:
    """Measure TRAIN rationale stance accuracy; no synthetic neutral labels."""
    scores = _logit_probabilities(model_logits, len(examples))
    confusion = {
        gold: {label: 0 for label in NLI_LABELS}
        for gold in ("entailment", "contradiction")
    }
    rows = []
    for sample, vector in zip(examples, scores, strict=True):
        gold = sample["gold"]
        if gold not in confusion:
            raise ValueError("Gold must be original SciFact SUPPORT/CONTRADICT")
        predicted = NLI_LABELS[int(np.argmax(vector))]
        confusion[gold][predicted] += 1
        rows.append({
            "claim_id": sample["claim_id"],
            "doc_id": sample["doc_id"],
            "rationale_sentence_ids": sample["sentence_indices"],
            "gold": gold,
            "predicted": predicted,
            "correct": gold == predicted,
            "scores_uncalibrated": {
                label: float(vector[i]) for i, label in enumerate(NLI_LABELS)
            },
        })
    counts = {gold: sum(values.values()) for gold, values in confusion.items()}
    if not all(counts.values()):
        raise ValueError("Two original TRAIN stance classes required")
    correct = sum(confusion[label][label] for label in confusion)
    accuracy = correct / len(rows)
    per_class_recall = {
        gold: confusion[gold][gold] / count for gold, count in counts.items()
    }
    return {
        "experiment_id": "M2-SCIFACT-ORIGINAL-STANCE-TRAIN-01",
        "status": "TRAIN_labeled_rationale_exploratory_no_runtime_changes",
        "dataset": "original SciFact claims_train + corpus",
        "source_url": SCIFACT_ARCHIVE_URL,
        "source_archive_sha256": archive_sha256,
        "source_licenses": {
            "claims_annotations": "CC BY 4.0",
            "corpus_abstracts": "ODC-By 1.0",
        },
        "model": {
            "id": DEFAULT_NLI_MODEL,
            "revision_if_available": model_revision,
            "label_order": list(NLI_LABELS),
        },
        "sample_count": len(rows),
        "gold_counts": counts,
        "prediction_counts": dict(Counter(row["predicted"] for row in rows)),
        "confusion": confusion,
        "accuracy_on_this_expert_labeled_TRAIN_rationale_sample": accuracy,
        "recall_by_gold_class": per_class_recall,
        "balanced_recall": sum(per_class_recall.values()) / len(per_class_recall),
        "neutral_gold_labels_in_sample": 0,
        "no_runtime_policy_changed": True,
        "limitations": [
            "Original SciFact TRAIN expert stance labels are genuine, not BEIR relevance qrels.",
            "The evaluation selects gold rationales directly; it does not measure retrieval.",
            "No negative/neutral ground truth is introduced via unrelated documents.",
            "Training-split accuracy on a small balanced sample is exploratory, not held-out.",
            "The NLI model is SNLI/MultiNLI-trained; biomedical transfer remains uncertain.",
            "Original train/dev/test split and archive SHA are retained; no TEST labels used.",
            "No decision threshold or RAG production default is modified.",
        ],
        "cases": rows,
    }


def gold_report_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Original SciFact TRAIN — Expert-labeled rationale stance evaluation",
        "",
        f"Archive SHA256: {report['source_archive_sha256']}",
        f"Sample count: {report['sample_count']} (balanced gold SUPPORT/CONTRADICT)",
        f"Sample TRAIN rationale stance accuracy: {report['accuracy_on_this_expert_labeled_TRAIN_rationale_sample']:.3f}",
        "",
        "| Gold stance | Predicted contradiction | Predicted entailment | Predicted neutral |",
        "|---|---:|---:|---:|",
    ]
    for gold, counts in report["confusion"].items():
        lines.append(
            f"| {gold} | {counts['contradiction']} | "
            f"{counts['entailment']} | {counts['neutral']} |"
        )
    lines += ["", "## Limitations", ""]
    lines.extend("- " + item for item in report["limitations"])
    return "\n".join(lines) + "\n"
