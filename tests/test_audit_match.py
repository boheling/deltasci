"""Tests for audit citation-matching heuristics.

These exist to lock in the behavior that:
- The BioIntel PMID 35562209 failure mode (AI asserts fabricated title metadata
  that disagrees with reality) is still caught.
- A terse author+year+ID citation is allowed through on identifier match alone
  when the AI does not assert metadata to disagree with.
"""

from __future__ import annotations

from deltasci.audit.citations._match import (
    claim_asserts_metadata,
    first_author_in_claim,
    title_close_match,
)
from deltasci.audit.extractor import Identifier


# --- title_close_match -------------------------------------------------------


def test_biointel_failure_mode_still_caught():
    """The BioIntel screenshot case: AI claims macrophage paper at PMID 35562209
    but the actual paper is renal pelvis adenocarcinoma. Their titles share
    nothing — must fail audit."""

    ai_claim = "Zhou Y, Yang D, Yang Q 2022, Nature Communications — Tumor-associated macrophage polarization in osteosarcoma microenvironment"
    actual = "Adenocarcinoma of the renal pelvis: Imaging findings and preliminary way of thinking in diagnosis"
    assert not title_close_match(ai_claim, actual)


def test_distinctive_project_name_passes():
    """A short citation that mentions the project name passes via distinctive-token bypass."""

    claim = "Pathak et al 2022, arXiv 2202.11214 — FourCastNet"
    actual = "FourCastNet: A Global Data-driven High-resolution Weather Model using Adaptive Fourier Neural Operators"
    assert title_close_match(claim, actual)


def test_bare_id_citation_passes():
    """A claim that's just author+year+ID with no asserted title metadata
    passes — the AI made no title claim to disagree with."""

    claim = "Pathak et al 2022, arXiv 2202.11214"
    actual = "FourCastNet: A Global Data-driven High-resolution Weather Model using Adaptive Fourier Neural Operators"
    assert title_close_match(claim, actual)


def test_high_overlap_passes():
    claim = "Smith et al 2020, weather model using neural operators on global data"
    actual = "Weather Model using Neural Operators on Global Data"
    assert title_close_match(claim, actual)


def test_zero_overlap_with_substantive_claim_fails():
    """If the AI provides a substantive but wrong title, fail."""

    claim = "Smith 2020, transplant immunology survival prediction graph network"
    actual = "Adenocarcinoma of the renal pelvis imaging diagnosis"
    assert not title_close_match(claim, actual)


# --- first_author_in_claim ---------------------------------------------------


def test_pubmed_format_first_author():
    """PubMed returns 'Family I' — last name comes first."""

    assert first_author_in_claim(["Pathak J"], "Pathak et al 2022")
    assert not first_author_in_claim(["Smith A"], "Pathak et al 2022")


def test_arxiv_format_first_author():
    """arXiv returns 'Given Family' — first name comes first."""

    assert first_author_in_claim(["Jaideep Pathak"], "Pathak et al 2022")
    assert first_author_in_claim(["Jaideep Pathak"], "Jaideep et al 2022")
    assert not first_author_in_claim(["Jaideep Pathak"], "Smith 2022")


def test_no_authors_returns_true():
    """Defensive: if API returned no authors, don't punish the claim."""

    assert first_author_in_claim([], "anything")
    assert first_author_in_claim([""], "anything")


# --- claim_asserts_metadata (bare-identifier gate) ---------------------------


def test_bare_identifier_asserts_no_metadata():
    """A source that is just the identifier asserts nothing to cross-check."""

    assert not claim_asserts_metadata("PMID 35562209", Identifier(kind="pmid", value="35562209", raw="PMID 35562209"))
    assert not claim_asserts_metadata(
        "arXiv:2502.14297", Identifier(kind="arxiv", value="2502.14297", raw="arXiv:2502.14297")
    )
    assert not claim_asserts_metadata(
        "10.1038/s41586-023-06792-0",
        Identifier(kind="doi", value="10.1038/s41586-023-06792-0", raw="10.1038/s41586-023-06792-0"),
    )


def test_real_citation_asserts_metadata():
    """An author/year/title cite still flows through the full per-field checks."""

    ident = Identifier(kind="pmid", value="35562209", raw="PMID 35562209")
    assert claim_asserts_metadata("Zhou Y 2022, Nature Comms — Tumor macrophages, PMID 35562209", ident)
    # A year alone is enough of an assertion to check.
    assert claim_asserts_metadata("Smith et al 2020, PMID 35562209", ident)
