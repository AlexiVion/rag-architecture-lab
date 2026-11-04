"""Opt-in strict citation v2 — no model, no source-claim entailment claims."""
from raglab.citations import validate_citations
from raglab.citations.validator_v2 import validate_citations_v2


def check(text, labels=("S1",), expected=True):
    result = validate_citations_v2(text, labels)
    assert result.citation_contract_passed is expected, (text, result)
    return result


def test_actual_m2_live02_answerable_post_period_source_is_syntactically_valid():
    draft = "Meridian Robotics developed the Orion Navigation System used by the Aster Rover. [S1]"
    assert not validate_citations(draft, ("S1",)).citation_contract_passed
    result = check(draft)
    assert result.sentence_count == 1
    assert result.cited_sentence_count == 1
    assert result.cited_labels == ("S1",)


def test_actual_m2_live02_irrelevant_source_label_fails_closed():
    draft = "Helios Instruments developed the Orion Navigation System for the Aster Rover [Solis Probe]."
    result = check(draft, expected=False)
    assert result.invalid_labels == ("Solis Probe",)
    assert result.valid_citation_count == 0


def test_actual_m2_live02_conflicting_date_uncited_stays_rejected():
    draft = "The Zenith Probe launched on July 9, 2021."
    result = check(draft, labels=("S1", "S2"), expected=False)
    assert result.citation_count == 0
    assert result.sentence_coverage == 0


def test_canonical_inline_and_post_period_forms_both_work():
    check("A source-grounded fact [S1].")
    check("A source-grounded fact. [S1]")
    check("A source-grounded fact!\n[S1]")
    check("Two-source claim. [S1][S2]", labels=("S1", "S2"))
    check("First claim. [S1] Second claim [S2].", labels=("S1", "S2"))
    check("First claim. [S1]\nSecond claim. [S2]", labels=("S1", "S2"))


def test_detached_label_does_not_cite_a_different_sentence():
    result = check("First claim. [S1] Second uncited claim.", expected=False)
    assert result.sentence_count == 2
    assert result.cited_sentence_count == 1
    assert result.sentence_coverage == 0.5
    result = check("First claim. [S1]\nSecond uncited claim.", expected=False)
    assert result.sentence_count == 2
    assert result.cited_sentence_count == 1


def test_no_empty_citation_only_or_prefix_citation_acceptance():
    result = check("[S1]", expected=False)
    assert result.sentence_count == 0
    check("[S1] Fact without trailing citation.", expected=False)
    check("Claim [S1] with uncited added text.", expected=False)
    check("INSUFFICIENT_EVIDENCE", expected=False)


def test_unknown_or_disallowed_labels_are_not_normalized():
    check("Claim. [S99]", expected=False)
    check("Claim [S1] [S99].", expected=False)
    check("Claim. [Other]", expected=False)
    check("Claim [Solis Probe].", expected=False)
    check("Claim [s1].", expected=False)
    check("Claim [S1].", labels=(), expected=False)


def test_multiple_sentence_coverage_rejects_partial_citation():
    check("One statement [S1]. Another unsupported statement.", expected=False)
    check("One statement. [S1] Another unsupported statement.", expected=False)
    result = check("One statement [S1]. Another supported statement [S1].")
    assert result.sentence_count == result.cited_sentence_count == 2


def test_v2_result_uses_same_immutable_report_interface():
    report = check("Claim [S1].")
    assert report.all_citations_valid
    assert report.citation_count == report.valid_citation_count == 1
    assert report.invalid_labels == ()
