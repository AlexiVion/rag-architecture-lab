from __future__ import annotations

import pytest

from raglab.core import Document
from scripts.micro.benchmark_micro_v02_cpu import benchmark,quantile

DOCS=[
    Document("a","entity: Station Aurora\nstart_year: 2012\nmanager: Camille\n"),
    Document("b","entity: Station Aurora\nstart_year: 2015\nmanager: Camille\n"),
]
CASES=[
    {"id":"x","question":"What is the start year for Station Aurora?",
     "expected_status":"CONFLICT"},
    {"id":"y","question":"Who is the manager of Station Aurora?",
     "expected_status":"ANSWER","expected_answer":"Camille"},
]


def test_cpu_profiler_counts_software_cost_and_is_not_neural_claim():
    report=benchmark(DOCS,CASES,top_ks=(1,3),iterations=2)
    assert report["model_calls"]==0
    assert len(report["configurations"])==2
    for config in report["configurations"]:
        assert config["strict_correct_visible_fixture"]==2
        assert config["wrong_accepts_visible_fixture"]==0
        assert config["sample_count"]==4
        assert config["total_reader_calls"]==8
        assert config["wall_ms"]["p95"]>=0
    assert "NOT_SCIENTIFIC" in report["status"]


def test_profiler_budget_and_quantiles():
    with pytest.raises(ValueError,match="Bounded"):
        benchmark(DOCS,CASES,iterations=0)
    with pytest.raises(ValueError,match="positive"):
        benchmark(DOCS,CASES,top_ks=(0,),iterations=1)
    assert quantile([1,2,3,4],0.95)==4
    with pytest.raises(ValueError,match="empty"):
        quantile([],0.95)
