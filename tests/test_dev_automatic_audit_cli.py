from raglab.cli import _build_parser


def test_dev_suite_auto_audit_command_is_noninteractive():
    args = _build_parser().parse_args([
        "audit-dev-suite",
        "--suite", "runs/dev-cases/M2-DEV-EVIDENCE-01_20261104T1433350834228Z",
    ])
    assert args.command == "audit-dev-suite"
    assert args.suite.endswith("M2-DEV-EVIDENCE-01_20261104T1433350834228Z")
