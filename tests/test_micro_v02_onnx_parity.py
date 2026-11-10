"""Finite, source-aligned ONNX vs FP32 parity test doubles (NO live model)."""
from __future__ import annotations

import numpy as np
import pytest

from raglab.evaluation.onnx_parity import _softmax, infer_onnx, compare_predictions


def _row(i: int, predicted: str | None = None) -> dict:
    expected = "contradiction" if i % 3 == 0 else "non_contradiction"
    return {
        "case_id": f"row-{i:03d}",
        "contradiction_id": str(i % 43),
        "expected": expected,
        "symmetric_prediction": predicted or expected,
    }


def _result(rows: list[dict], acc: float = 1.0, rec: float = 1.0,
            fp: int = 0) -> dict:
    return {
        "evaluation": {
            "cases": rows,
            "metrics": {
                "accuracy": acc,
                "balanced_accuracy": acc,
                "contradiction": {"recall": rec},
                "confusion": {
                    "true_non_contradiction_predicted_contradiction": fp
                },
            },
        }
    }


def test_stable_softmax_and_valid_class_count():
    p = _softmax(np.array([[10000.0, 9990.0, 9980.0], [-20., -20., -20.]]))
    assert p.shape == (2, 3)
    assert np.isfinite(p).all()
    assert p[0, 0] > 0.99
    assert p[1].sum() == pytest.approx(1.0)
    with pytest.raises(ValueError, match="three NLI"):
        _softmax(np.ones((2, 2)))


class Tokenized(dict):
    pass


class FakeTokenizer:
    def __call__(self, left, right, **kwargs):
        assert len(left) == len(right)
        assert kwargs["max_length"] == 512
        return Tokenized({
            "input_ids": np.ones((len(left), 5), dtype=np.int64),
            "attention_mask": np.ones((len(left), 5), dtype=np.int64),
        })


class Named:
    def __init__(self, name):
        self.name = name


class FakeSession:
    def __init__(self, inputs=None):
        self.inputs = inputs or ["input_ids", "attention_mask"]
        self.batches = []

    def get_inputs(self):
        return [Named(x) for x in self.inputs]

    def run(self, names, feed):
        assert names is None
        assert set(feed) == set(self.inputs)
        assert all(x.dtype == np.int64 for x in feed.values())
        n = feed["input_ids"].shape[0]
        self.batches.append(n)
        return [np.tile(np.array([[4.0, 2.0, 0.0]], dtype=np.float32), (n, 1))]


def test_inference_runs_both_pair_orders_and_counts_actual_batches():
    sess = FakeSession()
    a, b, costs = infer_onnx(
        sess, FakeTokenizer(), [("a", "b"), ("c", "d"), ("e", "f")],
        batch_size=2,
    )
    assert len(a) == len(b) == 3
    assert all(len(x) == 3 and sum(x) == pytest.approx(1) for x in a + b)
    assert sess.batches == [4, 2]
    assert costs["directional_inputs"] == 6
    assert costs["forward_batches"] == 2
    assert costs["input_tokens"] == 30
    assert costs["total_batch_wall_ms"] >= 0


def test_unrecognized_onnx_input_fails_closed():
    with pytest.raises(ValueError, match="Unrecognized ONNX inputs"):
        infer_onnx(FakeSession(["unknown"]), FakeTokenizer(), [("a", "b")])


def test_parity_success_and_quality_regression_are_separate_gates():
    a = [_row(i) for i in range(318)]
    b = [dict(x) for x in a]
    b[0]["symmetric_prediction"] = "non_contradiction"
    good = compare_predictions(_result(a), _result(b, acc=0.997, rec=0.991))
    assert good["agreement_count"] == 317
    assert good["changed_labels"] == 1
    assert good["engineering_gate"] == "PARITY_TOLERANCE_MET_ON_PUBLIC_BENCHMARK_ONLY"
    bad = compare_predictions(_result(a), _result(b, acc=0.8, rec=0.7, fp=5))
    assert bad["engineering_gate"] == "QUANTIZED_QUALITY_REGRESSION_NO_GO"
    assert bad["false_positive_int8"] == 5


def test_wrong_case_order_or_source_group_never_compares():
    a = [_row(i) for i in range(318)]
    b = [dict(x) for x in a]
    b[2]["contradiction_id"] = "wrong"
    with pytest.raises(ValueError, match="Unmatched"):
        compare_predictions(_result(a), _result(b))


def test_wrong_cardinality_never_compares():
    a = [_row(i) for i in range(318)]
    with pytest.raises(ValueError, match="exact 318"):
        compare_predictions(_result(a), _result(a[:-1]))
