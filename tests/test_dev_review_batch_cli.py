from raglab.cli import _build_parser


def test_dev_review_batch_cli_defaults():
    options = _build_parser().parse_args([
        "review-dev-batch",
        "--suite", "runs/dev-cases/M2-DEV-EVIDENCE-01_20261104T1433350834228Z",
    ])
    assert options.command == "review-dev-batch"
    assert options.max_cases == 3
