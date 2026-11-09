from raglab.cli import _build_parser


def test_retrieval_diagnosis_command_defaults_to_no_generation():
    args = _build_parser().parse_args(["diagnose-retrieval", "--query-id", "1"])
    assert args.command == "diagnose-retrieval"
    assert args.dataset == "beir/scifact/test"
    assert args.strategies == ["bm25", "dense", "hybrid"]
    assert args.candidate_k == 100
    assert args.context_k == 5
