from raglab.cli import _build_parser


def test_interactive_review_command_is_explicitly_human():
    args = _build_parser().parse_args(
        [
            "review-interactive",
            "--path", "runs/reviews/packet.json",
            "--output", "runs/reviews/annotated.json",
        ]
    )
    assert args.command == "review-interactive"
    assert args.path.endswith("packet.json")
    assert args.output.endswith("annotated.json")
