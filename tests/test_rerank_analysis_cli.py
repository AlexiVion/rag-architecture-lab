from raglab.cli import _build_parser


def test_offline_rerank_analyzer_parser():
    args = _build_parser().parse_args([
        "analyze-rerank", "--path", "benchmarks/results/fusion.json"
    ])
    assert args.command == "analyze-rerank"
    assert args.bootstrap_replicates == 2000
    assert args.seed == 42
