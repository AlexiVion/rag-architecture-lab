from raglab.citations import validate_citations


def test_no_citations_is_not_a_valid_citation_contract() -> None:
    report = validate_citations("A bare claim without support.", ["S1"])
    assert report.citation_count == 0
    assert not report.all_citations_valid
    assert not report.citation_contract_passed


def test_valid_label_coverage_does_not_claim_semantic_faithfulness() -> None:
    report = validate_citations("An unsupported claim [S1].", ["S1"])
    assert report.citation_contract_passed
    # A syntactically valid label cannot establish whether source S1 entails it.
