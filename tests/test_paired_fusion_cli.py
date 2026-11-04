from raglab.cli import _build_parser


def test_analyze_fusion_command_does_not_require_model_arguments():
    args = _build_parser().parse_args(
        ["analyze-fusion", "--path", "C:/results/fusion.json"]
    )
    assert args.command == "analyze-fusion"
    assert args.bootstrap_replicates == 2000
    assert args.seed == 42
