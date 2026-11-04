from raglab.cli import _build_parser


def test_nli_pilot_command_has_no_interactive_flags():
    args = _build_parser().parse_args([
        "nli-dev-pilot",
        "--suite", "runs/dev-cases/M2-DEV-EVIDENCE-01_example",
    ])
    assert args.command == "nli-dev-pilot"
    assert args.batch_size == 2
