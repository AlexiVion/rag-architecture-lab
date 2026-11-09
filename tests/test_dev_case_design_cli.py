from raglab.cli import _build_parser


def test_design_dev_cases_cli_defaults():
    args = _build_parser().parse_args(
        ["design-dev-cases", "--output-dir", "runs/dev-cases/new"]
    )
    assert args.dataset == "beir/scifact/train"
    assert args.query_count == 6
    assert args.seed == 17
