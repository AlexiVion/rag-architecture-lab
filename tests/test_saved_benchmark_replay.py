"""Archive import protects against cross-run/cross-cohort comparisons."""
import hashlib
import importlib.util
from pathlib import Path
import copy
import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("saved_benchmark", ROOT / "scripts/observatory/export_saved_benchmark_replay.py")
assert SPEC and SPEC.loader
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


def archive():
    def result(pipeline):
        return {"pipeline": pipeline, "dataset": "beir/scifact/test",
            "query_count": 2, "document_count": 5183,
            "environment": {"python": "3.11", "platform": "local"},
            "queries": [
                {"query_id":"1","query":"source claim one","results":[{"doc_id":"a","rank":1,"score":1.3},{"doc_id":"b","rank":2,"score":0.9}]},
                {"query_id":"2","query":"source claim two","results":[{"doc_id":"b","rank":1,"score":0.2},{"doc_id":"a","rank":2,"score":0.1}]},
            ]}
    return {"dataset":"beir/scifact/test","pipelines":["bm25","hybrid"],
            "results":[result("bm25"),result("hybrid")]}


def test_export_persists_original_first_query_ranks_and_archive_digest():
    source = archive()
    result = mod.export_saved_benchmark(source,source_sha256="a"*64,take=1)
    assert result["status"]=="archived_original_per_query_not_independently_revalidated"
    assert result["pipeline_names"]==["bm25","hybrid"]
    assert len(result["queries"])==1
    assert result["queries"][0]["rankings"]["hybrid"][0]["doc_id"]=="a"
    assert result["source_archive_sha256"]=="a"*64


def test_export_rejects_mismatched_question_or_environment():
    source = archive()
    source["results"][1]["queries"][0]["query"] = "changed question"
    with pytest.raises(ValueError,match="queries mismatch"):
        mod.export_saved_benchmark(source,source_sha256="a"*64)
    source = archive()
    source["results"][1]["environment"]["platform"]="other host"
    with pytest.raises(ValueError,match="environment"):
        mod.export_saved_benchmark(source,source_sha256="a"*64)


def test_export_rejects_duplicate_ids_or_forged_rank():
    source = archive()
    source["results"][0]["queries"][0]["results"][1]["doc_id"]="a"
    with pytest.raises(ValueError,match="duplicate"):
        mod.export_saved_benchmark(source,source_sha256="a"*64)
    source = archive()
    source["results"][0]["queries"][0]["results"][0]["rank"]=3
    with pytest.raises(ValueError,match="rank"):
        mod.export_saved_benchmark(source,source_sha256="a"*64)
