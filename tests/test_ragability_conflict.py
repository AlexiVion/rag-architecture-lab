from __future__ import annotations

import csv

import pytest

from raglab.evaluation.ragability_conflict import (
    CONFLICT,
    DATASET_ROWS,
    NON_CONFLICT,
    PAIR_SPECS,
    build_conflict_pairs,
    dataset_manifest,
    read_ragability_tsv,
    score_model_rows,
)


FIELDS = [
    "contradiction_ID",
    "WikiContradict_ID",
    "reasoning_required_c1c2",
    "context_1",
    "context_2",
    "context_3_nc1_c2",
    "context_4_nc1_nc2_nc3",
    "query_text",
]


def sample_rows():
    rows = []
    for i in range(53):
        group = i + 1 if i < 43 else i - 42
        rows.append({
            "contradiction_ID": str(group),
            # The published corpus contains a row with no WikiContradict ID.
            "WikiContradict_ID": "" if i == 41 else str(group + 100),
            "reasoning_required_c1c2": (
                "temporal.numerical" if i % 2 else "categorical"
            ),
            "context_1": f"Station {group} was founded in 2001.",
            "context_2": f"Station {group} was founded in 2002.",
            "context_3_nc1_c2": f"Station {group} was founded in 2001.",
            "context_4_nc1_nc2_nc3": f"Station {group} is located in Dola.",
            "query_text": f"When was Station {group} founded?",
        })
    return rows


def write_tsv(path, rows):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream, fieldnames=FIELDS, delimiter="\t", quoting=csv.QUOTE_MINIMAL
        )
        writer.writeheader()
        writer.writerows(rows)


def test_reader_and_builder_validate_exact_external_corpus_shape(tmp_path):
    path = tmp_path / "ragability.tsv"
    write_tsv(path, sample_rows())
    rows = read_ragability_tsv(path)
    pairs = build_conflict_pairs(rows)
    assert len(rows) == DATASET_ROWS
    assert len({row["contradiction_ID"] for row in rows}) == 43
    assert len(PAIR_SPECS) == 6
    assert len(pairs) == 318
    assert sum(pair.expected == CONFLICT for pair in pairs) == 106
    assert sum(pair.expected == NON_CONFLICT for pair in pairs) == 212
    assert {pair.pair_type for pair in pairs} == {
        "c1_c2", "c2_c3", "c1_c3", "c1_c4", "c2_c4", "c3_c4"
    }


def test_dataset_manifest_preserves_license_and_group_not_row_independence(tmp_path):
    path = tmp_path / "ragability.tsv"
    write_tsv(path, sample_rows())
    rows = read_ragability_tsv(path)
    pairs = build_conflict_pairs(rows)
    manifest = dataset_manifest(
        rows, pairs, source_sha256="a" * 64
    )
    assert manifest["row_count"] == 53
    assert manifest["unique_conflict_groups"] == 43
    assert manifest["pair_count"] == 318
    assert manifest["license"] == "cc-by-sa-4.0"
    assert manifest["rows_without_wiki_contradict_cross_reference"] == 1
    assert "public exposed benchmark" in " ".join(manifest["limitations"])


def test_reader_fails_closed_on_row_count_or_group_leakage(tmp_path):
    path = tmp_path / "ragability.tsv"
    write_tsv(path, sample_rows()[:-1])
    with pytest.raises(ValueError, match="exactly 53"):
        read_ragability_tsv(path)

    rows = sample_rows()
    for row in rows:
        row["contradiction_ID"] = "1"
    write_tsv(path, rows)
    with pytest.raises(ValueError, match="43"):
        read_ragability_tsv(path)


def test_three_way_nli_scores_become_binary_conflict_decisions():
    rows = sample_rows()
    pairs = build_conflict_pairs(rows)
    forward = []
    reverse = []
    for pair in pairs:
        if pair.expected == CONFLICT:
            score = [0.90, 0.05, 0.05]
        else:
            score = [0.05, 0.05, 0.90]
        forward.append(score)
        reverse.append(score)
    report = score_model_rows(
        pairs, forward, reverse, bootstrap_repetitions=100
    )
    metrics = report["metrics"]
    assert metrics["accuracy"] == 1.0
    assert metrics["balanced_accuracy"] == 1.0
    assert metrics["macro_f1"] == 1.0
    assert metrics["contradiction"]["recall"] == 1.0
    assert metrics["directional_prediction_agreement"] == 1.0
    assert metrics["always_non_contradiction_baseline"]["balanced_accuracy"] == 0.5
    assert report["pair_type_metrics"]["c1_c2"]["accuracy"] == 1.0
    assert report["pair_type_metrics"]["c1_c2"]["expected_label"] == CONFLICT
    assert report["pair_type_metrics"]["c1_c3"]["expected_label"] == NON_CONFLICT
    assert report["reasoning_type_metrics"]["categorical"]["n"] == 27
    assert report["reasoning_type_metrics"]["temporal.numerical"]["n"] == 26
    assert report["reasoning_type_metrics"]["categorical"]["gold_label"] == CONFLICT
    assert report["group_bootstrap"]["repetitions"] == 100
    assert len(report["group_bootstrap"]["balanced_accuracy_percentile_95_ci"]) == 2


def test_symmetric_mapping_does_not_treat_entailment_and_neutral_as_conflict():
    rows = sample_rows()
    pairs = build_conflict_pairs(rows)
    forward = []
    reverse = []
    for pair in pairs:
        if pair.expected == CONFLICT:
            forward.append([0.8, 0.1, 0.1])
            reverse.append([0.8, 0.1, 0.1])
        else:
            # Either NLI entailment or neutral means "not a contradiction"
            # for this binary benchmark, not an unsupported third gold class.
            forward.append([0.05, 0.90, 0.05])
            reverse.append([0.05, 0.05, 0.90])
    report = score_model_rows(
        pairs, forward, reverse, bootstrap_repetitions=100
    )
    assert report["metrics"]["accuracy"] == 1.0
    assert report["cases"][2]["symmetric_nli_label"] == "entailment"
    assert report["cases"][2]["symmetric_prediction"] == NON_CONFLICT
    assert report["cases"][2]["directional_agreement"] is True


def test_pair_provenance_does_not_copy_dataset_text():
    pair = build_conflict_pairs(sample_rows())[0]
    public = pair.public_dict()
    assert "premise" not in public
    assert "hypothesis" not in public
    assert len(public["premise_sha256"]) == 64
    assert len(public["hypothesis_sha256"]) == 64
