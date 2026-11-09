from raglab.cli import _build_parser


def test_fusion_study_defaults_to_train_only():
    args = _build_parser().parse_args(["fusion-study"])
    assert args.dataset == "beir/scifact/train"
    assert args.allow_test is False
    assert args.weights == [1.5, 2.0, 3.0]
    assert args.k == [5, 10]
