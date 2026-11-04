from raglab.cli import _build_parser


def test_original_scifact_stance_command_no_user_questions():
    args = _build_parser().parse_args(["evaluate-original-scifact-stances"])
    assert args.command == "evaluate-original-scifact-stances"
    assert args.per_class == 20
    assert args.seed == 17
    assert args.archive.endswith("data.tar.gz")
