"""Deterministic natural-language SQuAD v2 *DEV* retrieval benchmark adapter.

Uses official public SQuAD v2 DEV data, pinned by SHA256. This is an exploratory
published DEV dataset, never an untouched external holdout. SQuAD license:
CC BY-SA 4.0; cite Rajpurkar et al. 2018. No dataset is committed to git.
"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from raglab.micro.experiment import MicroDataset, parse_dataset

SQUAD_V2_DEV_URL = "https://rajpurkar.github.io/SQuAD-explorer/dataset/dev-v2.0.json"
SQUAD_V2_DEV_SHA256 = "80a5225e94905956a6446d296ca1093975c4d3b3260f1d6c8f68bc2ab77182d8"


@dataclass(frozen=True, slots=True)
class GoldReference:
    case_id: str
    answers: tuple[str, ...]
    answerable: bool
    gold_doc_id: str
    official_title: str


@dataclass(frozen=True, slots=True)
class NaturalQABenchmark:
    dataset: MicroDataset
    references: dict[str, GoldReference]
    source_sha256: str
    source_name: str
    source_license: str
    sampling_version: str

    def manifest(self) -> dict:
        return {
            "source": self.source_name,
            "source_sha256": self.source_sha256,
            "source_license": self.source_license,
            "sampling_version": self.sampling_version,
            "dataset_fingerprint": self.dataset.fingerprint,
            "split": "dev_exploratory_not_unseen_holdout",
            "cases": len(self.dataset.cases),
            "documents": len(self.dataset.documents),
            "answerable": sum(ref.answerable for ref in self.references.values()),
            "unanswerable": sum(not ref.answerable for ref in self.references.values()),
            "distinct_articles": len({r.official_title for r in self.references.values()}),
            "limitations": [
                "SQuAD v2 DEV is publicly exposed; model training contamination is possible",
                "Official short-answer references do not verify source-supported reasoning",
                "Selected questions are balanced by answerability, not a random prevalence sample",
                "Document corpus is a curated public DEV subset with distractors, not open web",
                "No official hidden SQuAD test data is used",
            ],
        }


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _doc_id(title: str, context: str) -> str:
    return "squad2-" + _sha(title + "\x00" + context)[:24]


def _split(title: str) -> str:
    # Distinct article groups never enter two partitions, by construction.
    bucket = int(_sha("micro-squad2-v1-article:" + title)[:8], 16) % 10
    if bucket < 6:
        return "dev"
    if bucket < 8:
        return "calibration"
    return "holdout"


def load_official_squad_dev(
    path: str | Path,
    *,
    expected_sha256: str = SQUAD_V2_DEV_SHA256,
    max_cases: int = 8,
    distractors: int = 96,
    split: str = "dev",
) -> NaturalQABenchmark:
    """Select balanced, natural questions without reading scoring outputs.

    Never open calibration or holdout through this default public runner; those
    require a pre-registered independent protocol and a separate permission.
    """
    if split != "dev":
        raise ValueError("Public MICRO benchmark deliberately allows DEV only")
    if max_cases <= 0 or max_cases % 2 or distractors < 0:
        raise ValueError("max_cases must be a positive even integer; distractors >=0")
    data_bytes = Path(path).read_bytes()
    digest = hashlib.sha256(data_bytes).hexdigest()
    if digest != expected_sha256:
        raise ValueError(f"SQuAD v2 DEV SHA256 mismatch: {digest}")
    raw = json.loads(data_bytes)
    if raw.get("version") != "v2.0" or not isinstance(raw.get("data"), list):
        raise ValueError("Not official SQuAD v2 JSON")
    by_title: dict[str, dict[str, list[dict[str, Any]]]] = {}
    distractor_pool: dict[str, tuple[str, str]] = {}
    for article in raw["data"]:
        title = str(article["title"])
        if _split(title) != "dev":
            continue
        kinds = by_title.setdefault(title, {"answerable": [], "unanswerable": []})
        for paragraph in article["paragraphs"]:
            context = paragraph["context"]
            doc_id = _doc_id(title, context)
            distractor_pool[doc_id] = (title, context)
            for qa in paragraph["qas"]:
                impossible = qa.get("is_impossible") is True
                answers = tuple(a["text"] for a in qa.get("answers", []))
                if impossible and answers:
                    raise ValueError("Official impossible question contains answers")
                if not impossible and not answers:
                    continue
                if not impossible:
                    # Check the original exact annotation offsets: never accept
                    # a purported gold span outside the original paragraph.
                    if not all(
                        context[a["answer_start"]: a["answer_start"] + len(a["text"])]
                        == a["text"]
                        for a in qa["answers"]
                    ):
                        continue
                item = {
                    "id": qa["id"],
                    "question": qa["question"],
                    "title": title,
                    "doc_id": doc_id,
                    "answers": answers,
                    "answerable": not impossible,
                }
                kinds["unanswerable" if impossible else "answerable"].append(item)

    # Group-preserving, hash-seeded selection; one positive and negative per
    # article each pass, preferring distinct articles before additional items.
    eligible = [
        title for title, kinds in by_title.items()
        if kinds["answerable"] and kinds["unanswerable"]
    ]
    eligible.sort(key=lambda title: _sha("micro-v1-order:" + title))
    if len(eligible) * 2 < max_cases:
        raise ValueError("Not enough independent articles for requested pilot")
    chosen: list[dict[str, Any]] = []
    for title in eligible[: max_cases // 2]:
        for kind in ("answerable", "unanswerable"):
            values = by_title[title][kind]
            chosen.append(min(values, key=lambda row: _sha("micro-v1-qa:" + row["id"])))

    used = {item["doc_id"] for item in chosen}
    remaining = sorted(
        (doc_id for doc_id in distractor_pool if doc_id not in used),
        key=lambda doc_id: _sha("micro-v1-distractor:" + doc_id),
    )
    docs_ids = sorted(used | set(remaining[:distractors]))
    docs = []
    for doc_id in docs_ids:
        title, text = distractor_pool[doc_id]
        docs.append({"id": doc_id, "title": title, "text": text})
    cases = []
    references: dict[str, GoldReference] = {}
    for item in chosen:
        case_id = item["id"]
        cases.append(
            {
                "id": case_id,
                "question": item["question"],
                "group_id": item["title"],
                "split": "dev",
                "oracle_doc_ids": [item["doc_id"]],
            }
        )
        references[case_id] = GoldReference(
            case_id,
            item["answers"],
            item["answerable"],
            item["doc_id"],
            item["title"],
        )
    dataset = parse_dataset(
        {
            "schema_version": 1,
            "dataset_id": "SQuAD2-v2.0-DEV-MICRO-hashgroup-v1",
            "fixture_only": False,
            "documents": docs,
            "cases": cases,
        }
    )
    return NaturalQABenchmark(
        dataset=dataset,
        references=references,
        source_sha256=digest,
        source_name=SQUAD_V2_DEV_URL,
        source_license="CC-BY-SA-4.0",
        sampling_version="micro-squad-v1-article-grouped-balanced-dev",
    )
