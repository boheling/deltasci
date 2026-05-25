"""Tests for the audit intake adapter (text/records/bibtex → Claim)."""

from __future__ import annotations

from deltasci.audit.cache import AuditCache
from deltasci.audit.intake import (
    Claim,
    claims_from_source,
    detect_format,
    from_bibtex,
    from_records,
    from_tagged_text,
    from_text,
    split_stats,
)
from deltasci.audit.runner import MultiLayerAuditor
from deltasci.audit.base import AuditFinding, Auditor


def test_from_tagged_text_extracts_claim_and_source():
    text = (
        'intro [CLAIM type=published-evidence coverage=well-covered '
        'source="Smith 2020, PMID 12345678"]TAMs drive progression.[/CLAIM] outro'
    )
    claims = from_tagged_text(text)
    assert claims == [Claim(claim="TAMs drive progression.", source="Smith 2020, PMID 12345678")]


def test_from_text_keeps_only_cited_sentences():
    text = "TAMs dominate the microenvironment (PMID 35562209). The sky is blue."
    claims = from_text(text)
    assert len(claims) == 1
    assert "35562209" in claims[0].source
    assert claims[0].claim.startswith("TAMs dominate")


def test_split_stats_counts_cited_and_uncited():
    text = "A real claim with arXiv:2502.14297 here. An uncited sentence. Another doi 10.1038/nature01."
    cited, uncited = split_stats(text)
    assert cited == 2
    assert uncited == 1


def test_from_text_handles_bullets():
    text = "- First finding, see PMID 11111111.\n- Second, no citation here."
    claims = from_text(text)
    assert len(claims) == 1
    assert not claims[0].claim.startswith("-")


def test_from_records_parses_json_array():
    claims = from_records('[{"claim": "x", "source": "PMID 1"}, {"claim": "y"}]')
    assert claims[0] == Claim(claim="x", source="PMID 1")
    assert claims[1] == Claim(claim="y", source="")


def test_from_bibtex_builds_source_from_fields():
    bib = """
@article{smith2020,
  title = {A study of macrophages},
  doi = {10.1038/nature12345},
  year = {2020}
}
"""
    claims = from_bibtex(bib)
    assert len(claims) == 1
    assert claims[0].claim == "A study of macrophages"
    assert "10.1038/nature12345" in claims[0].source


def test_detect_format():
    assert detect_format("[CLAIM type=x]a[/CLAIM]") == "tagged"
    assert detect_format('[{"claim": "x"}]') == "records"
    assert detect_format("@article{k, title={t}}") == "bibtex"
    assert detect_format("Just some prose with PMID 12345678.") == "text"


def test_claims_from_source_auto_dispatch():
    assert claims_from_source("[CLAIM type=x coverage=sparse source=\"S\"]body[/CLAIM]")[0].source == "S"
    assert claims_from_source('[{"claim":"c","source":"PMID 9"}]')[0].claim == "c"


class _MockPMIDVerifier(Auditor):
    name = "pubmed"

    def can_audit(self, target):
        return target.get("identifier") and target["identifier"].kind == "pmid"

    def audit(self, target):
        return AuditFinding(
            target_kind="citation",
            target_summary=target["claim_source"],
            auditor_name=self.name,
            status="verified",
        )


def test_claims_duck_type_through_runner(tmp_path):
    """A Claim (not an EvidenceItem) must flow through the runner unchanged."""
    claims = claims_from_source("TAMs drive things (PMID 12345678).")
    auditor = MultiLayerAuditor(
        auditors=[_MockPMIDVerifier()], cache=AuditCache(tmp_path / "c.json")
    )
    report = auditor.audit(claims)
    assert report.verified_count == 1
