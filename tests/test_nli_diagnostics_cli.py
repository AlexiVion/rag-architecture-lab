from raglab.cli import _build_parser


def test_nli_diagnosis_command_is_noninteractive():
    args = _build_parser().parse_args([
        "diagnose-nli", "--suite", "runs/dev-cases/M2-DEV-EVIDENCE-01_local",
    ])
    assert args.command == "diagnose-nli"
