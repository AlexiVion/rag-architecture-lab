# Real repository retrieval replay

This is an actual, offline Python retrieval execution over eight versioned research documents in the repository. It is deliberately NOT the original BEIR SciFact experiment. Its three questions are authored, with no ground-truth relevance labels; therefore no MRR, Recall, factual QA, or model-quality comparison is claimed.

Two existing architecture implementations are executed: BM25 on full documents, and parent-child BM25 using 480-character child passages (60-character overlap) with parent aggregation. Scores are incomparable across the two strategies; visual comparison is by document order only.

Generate and verify from the repository root, after installing the normal Python development environment:

    python scripts/observatory/export_repo_retrieval_replay.py
    python scripts/observatory/export_repo_retrieval_replay.py --check
    python -m pytest -q tests/test_repo_retrieval_replay.py

The output, experiments/repo_retrieval_replay.json, contains original document IDs, source links, SHA256s, corpus and code fingerprints, pipeline parameters, top-five rankings, and explicit null relevance/answer fields. It includes no copied full research texts or inference secrets.

The source selection and questions are predefined. Re-run and review the artifact after modifying any tracked source file. Experimental and academic conclusions require separate labelled, matched studies under docs/EXPERIMENT_PROTOCOL.md.

Actual individual SciFact rankings cannot be reconstructed from published V0/V1 aggregate numbers. A separate import tool should only accept archived real raw benchmark JSON with compatible query IDs and dataset identity.

## Observatory integration

The Experiments section now offers a dedicated read-only comparison of the authentic saved Python top-five rank lists, preserving original document identities, stable source hashes and source links. It does not re-label these unannotated repository queries as the measured SciFact benchmark; the original V0/V1 benchmark reports remain separate.
