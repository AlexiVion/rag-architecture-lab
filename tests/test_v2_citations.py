from raglab.citations import validate_citations


def test_citation_validator_detects_valid_and_invalid_labels() -> None:
    report = validate_citations(
        "Claim one [S1]. Claim two [S3].",
        ["S1", "S2"],
    )

    assert report.cited_labels == ("S1", "S3")
    assert report.invalid_labels == ("S3",)
    assert report.valid_citation_count == 1
    assert report.citation_count == 2
    assert not report.all_citations_valid


def test_citation_validator_reports_sentence_coverage() -> None:
    report = validate_citations(
        "Supported claim [S1]. Unsupported-looking sentence.",
        ["S1"],
    )

    assert report.sentence_count == 2
    assert report.cited_sentence_count == 1
    assert report.sentence_coverage == 0.5
