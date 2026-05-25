"""Tests for the deterministic ClaimSupportAuditor (claim-to-abstract topical support)."""

from __future__ import annotations

from deltasci.audit.extractor import Identifier
from deltasci.audit.support import ClaimSupportAuditor, salient_terms

# A renal-cancer abstract — the BioIntel decoy. A macrophage claim citing this PMID
# should be flagged UNSUPPORTED (wrong paper), even though the PMID is real.
_RENAL_ABSTRACT = (
    "Primary adenocarcinoma of the renal pelvis is a rare malignancy. We report a case "
    "presenting with hematuria and flank pain, treated with nephroureterectomy. Histology "
    "confirmed mucinous adenocarcinoma with urothelial components."
)
_MACROPHAGE_ABSTRACT = (
    "Tumor-associated macrophages (TAMs) polarized to an M2 phenotype dominate the "
    "osteosarcoma microenvironment and drive immunosuppression and metastatic progression."
)


def _target(pmid: str, claim_text: str) -> dict:
    return {
        "identifier": Identifier(kind="pmid", value=pmid, raw=f"PMID {pmid}"),
        "claim_text": claim_text,
        "claim_source": f"PMID {pmid}",
    }


def test_salient_terms_keeps_markers_drops_stopwords():
    terms = salient_terms("The TFE3 fusion drives the tumor with CD8 cells")
    assert "tfe3" in terms
    assert "cd8" in terms
    assert "the" not in terms


def test_support_flags_wrong_paper(monkeypatch):
    monkeypatch.setattr("deltasci.audit.support.fetch_abstract", lambda pmid, timeout=10.0: _RENAL_ABSTRACT)
    finding = ClaimSupportAuditor().audit(
        _target("35562209", "M2-polarized tumor-associated macrophages dominate the osteosarcoma microenvironment.")
    )
    assert finding.status == "mismatch"
    assert finding.target_kind == "support"
    assert "wrong paper" in finding.mismatch_reasons[0]


def test_support_ignores_identifier_tokens_in_claim(monkeypatch):
    """The efetch abstract echoes 'PMID: <n>'; the inlined identifier in the claim must
    not count as a shared term and inflate overlap (the bug that masked a wrong cite)."""
    abstract = "PMID: 35562209. Adenocarcinoma of the renal pelvis: imaging findings and diagnosis."
    monkeypatch.setattr("deltasci.audit.support.fetch_abstract", lambda pmid, timeout=10.0: abstract)
    finding = ClaimSupportAuditor().audit(
        _target(
            "35562209",
            "M2-polarized tumor-associated macrophages dominate the osteosarcoma microenvironment (PMID 35562209).",
        )
    )
    assert finding.status == "mismatch"
    assert "35562209" not in finding.fetched_metadata.get("overlap_terms", [])


def test_support_passes_matching_paper(monkeypatch):
    monkeypatch.setattr("deltasci.audit.support.fetch_abstract", lambda pmid, timeout=10.0: _MACROPHAGE_ABSTRACT)
    finding = ClaimSupportAuditor().audit(
        _target("99999999", "M2 tumor-associated macrophages dominate the osteosarcoma microenvironment.")
    )
    assert finding.status == "verified"
    assert finding.confidence == "medium"  # honest: it's a heuristic, not a proof


def test_support_abstains_on_short_claim(monkeypatch):
    monkeypatch.setattr("deltasci.audit.support.fetch_abstract", lambda pmid, timeout=10.0: _MACROPHAGE_ABSTRACT)
    finding = ClaimSupportAuditor().audit(_target("1", "It works."))
    assert finding.status == "unverifiable"


def test_support_skips_on_fetch_failure(monkeypatch):
    monkeypatch.setattr("deltasci.audit.support.fetch_abstract", lambda pmid, timeout=10.0: None)
    finding = ClaimSupportAuditor().audit(_target("1", "A reasonably long macrophage osteosarcoma claim here."))
    assert finding.status == "skipped"


def test_can_audit_requires_pmid_and_skips_quoted_claims():
    aud = ClaimSupportAuditor()
    assert aud.can_audit(_target("123", "an unquoted claim about macrophages and tumors"))
    # A claim carrying a verbatim quote is owned by QuoteInAbstractAuditor.
    quoted = _target("123", 'the paper states "macrophages dominate the microenvironment here"')
    assert not aud.can_audit(quoted)
    # Non-pmid identifiers are out of scope for v1.
    doi_target = {
        "identifier": Identifier(kind="doi", value="10.1/x", raw="10.1/x"),
        "claim_text": "some claim",
        "claim_source": "10.1/x",
    }
    assert not aud.can_audit(doi_target)
