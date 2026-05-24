from __future__ import annotations

from deltasci.grounding import check_against_rules, extract_signals


def test_extract_well_formed_claims():
    text = """
[CLAIM type=published-evidence coverage=well-covered source="Doe 2023, Nature 1:2"]first claim[/CLAIM]
[CLAIM type=observation coverage=sparse source=""]second claim[/CLAIM]
""".strip()
    report = extract_signals(text)
    assert report.ok
    assert len(report.items) == 2
    assert report.items[0].coverage == "well-covered"
    assert report.items[1].coverage == "sparse"


def test_extract_unknown_type_is_violation():
    text = '[CLAIM type=made-up coverage=well-covered source=""]bad[/CLAIM]'
    report = extract_signals(text)
    assert not report.ok
    assert "evidence type" in report.violations[0].reason


def test_extract_missing_coverage_is_violation():
    text = '[CLAIM type=observation source=""]missing coverage[/CLAIM]'
    report = extract_signals(text)
    assert not report.ok
    assert "coverage" in report.violations[0].reason.lower()


def test_extract_uncovered_on_claim_is_rejected_with_helpful_message():
    text = '[CLAIM type=observation coverage=uncovered source=""]should be a gap, not a claim[/CLAIM]'
    report = extract_signals(text)
    assert not report.ok
    assert "KNOWLEDGE_GAP" in report.violations[0].reason


def test_extract_missing_source_for_evidence_is_violation():
    text = '[CLAIM type=published-evidence coverage=well-covered]missing source[/CLAIM]'
    report = extract_signals(text)
    assert not report.ok


def test_extract_knowledge_gap():
    text = '[KNOWLEDGE_GAP category=lab-tribal-knowledge]What is the local lab convention?[/KNOWLEDGE_GAP]'
    report = extract_signals(text)
    assert report.ok
    assert len(report.knowledge_gaps) == 1
    assert report.knowledge_gaps[0].category == "lab-tribal-knowledge"
    assert "local lab" in report.knowledge_gaps[0].question


def test_extract_knowledge_gap_default_category():
    text = '[KNOWLEDGE_GAP]What is the answer?[/KNOWLEDGE_GAP]'
    report = extract_signals(text)
    assert report.ok
    assert report.knowledge_gaps[0].category == "other"


def test_extract_knowledge_gap_unknown_category_is_violation():
    text = '[KNOWLEDGE_GAP category=made-up-category]?[/KNOWLEDGE_GAP]'
    report = extract_signals(text)
    assert not report.ok


def test_extract_novel_synthesis():
    text = '[NOVEL_SYNTHESIS rationale="links two areas"]A and B can be combined in this new way.[/NOVEL_SYNTHESIS]'
    report = extract_signals(text)
    assert report.ok
    assert len(report.novel_syntheses) == 1
    assert report.novel_syntheses[0].rationale == "links two areas"


def test_extract_novel_synthesis_no_rationale():
    text = '[NOVEL_SYNTHESIS]A leap.[/NOVEL_SYNTHESIS]'
    report = extract_signals(text)
    assert report.ok
    assert report.novel_syntheses[0].rationale == ""


def test_pack_evidence_rule_pattern_violation():
    text = '[CLAIM type=published-evidence coverage=well-covered source="No year here"]bad source[/CLAIM]'
    report = extract_signals(text)
    assert report.ok  # passes structural validation
    rules = [{"type": "published-evidence", "source_pattern": r"\d{4}"}]
    report = check_against_rules(report, rules)
    assert not report.ok
    assert "pattern" in report.violations[0].reason.lower()


def test_pack_evidence_rule_pattern_pass():
    text = '[CLAIM type=published-evidence coverage=well-covered source="Doe 2023, Nature 1:2"]ok[/CLAIM]'
    report = extract_signals(text)
    rules = [{"type": "published-evidence", "source_pattern": r"\d{4}"}]
    report = check_against_rules(report, rules)
    assert report.ok
    assert len(report.items) == 1


def test_attribute_order_independence():
    """Tag attributes can appear in any order."""

    text = '[CLAIM source="Doe 2023" coverage=well-covered type=published-evidence]ok[/CLAIM]'
    report = extract_signals(text)
    assert report.ok
    assert len(report.items) == 1
