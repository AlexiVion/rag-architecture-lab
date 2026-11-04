from raglab.cli import _build_parser


def test_review_export_cli_parameters():
    args = _build_parser().parse_args([
        "review-export", "--path", "runs/v2/answer.json",
        "--output", "runs/reviews/review.json",
    ])
    assert args.command == "review-export"
    assert args.output.endswith("review.json")


def test_review_score_cli_parameters():
    args = _build_parser().parse_args([
        "review-score", "--path", "runs/reviews/review.json",
    ])
    assert args.command == "review-score"
    assert args.output is None
