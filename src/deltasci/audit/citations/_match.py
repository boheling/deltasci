"""Heuristics for comparing AI-claimed citation metadata against API-returned metadata."""

from __future__ import annotations

import re
import unicodedata


def normalize(s: str) -> str:
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = s.encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"[^a-z0-9\s]", " ", s.lower())
    return re.sub(r"\s+", " ", s).strip()


def title_close_match(claim: str, actual: str, min_token_overlap: float = 0.3) -> bool:
    """Token-overlap heuristic — paper titles in citations often abbreviate or paraphrase.

    Returns True if ANY of:
      - the claim is too short to carry meaningful title metadata (just an
        author+year+ID cite); we trust the ID match alone.
      - the claim contains any 6+ char distinctive token from the actual title
        (project names like "FourCastNet" are very specific).
      - at least `min_token_overlap` of the actual title's 4+ char tokens appear
        in the claim.

    Generous on purpose: we're catching "fabricated unrelated paper" (the BioIntel
    PMID 35562209 case), not enforcing exact title match. The PMID 35562209 BioIntel
    failure had AI-asserted title metadata that disagreed with reality; bare-ID
    citations have no asserted title to disagree.
    """

    norm_claim = normalize(claim)
    norm_actual_tokens = set(t for t in normalize(actual).split() if len(t) >= 4)
    if not norm_actual_tokens:
        return False

    # Bare-ID citation bypass: claim has very few content tokens beyond the
    # identifier itself. Author + year + ID = ~5-7 tokens is normal sparse cite.
    claim_content_tokens = [t for t in norm_claim.split() if len(t) >= 4]
    if len(claim_content_tokens) <= 5:
        return True

    # Distinctive-token bypass: any 6+ char token from the actual title in the claim.
    distinctive = {t for t in norm_actual_tokens if len(t) >= 6}
    if any(t in norm_claim for t in distinctive):
        return True

    overlap = sum(1 for t in norm_actual_tokens if t in norm_claim)
    return (overlap / len(norm_actual_tokens)) >= min_token_overlap


def first_author_in_claim(actual_authors: list[str], claim: str) -> bool:
    """Format-agnostic first-author check.

    PubMed/Crossref give "Pathak J" (family-then-initial); arXiv gives
    "Jaideep Pathak" (given-then-family). We don't try to disambiguate —
    we just require ANY of the multi-character tokens in the author name
    to appear in the claim. A 4+ char token match is robust to both formats.
    """

    if not actual_authors:
        return True
    first = actual_authors[0].strip()
    if not first:
        return True
    parts = [p for p in re.split(r"[,\s]+", first) if len(p) >= 4]
    if not parts:
        # Single-initial or short-name authors — fall back to any-token-in-claim.
        parts = [p for p in re.split(r"[,\s]+", first) if p]
    if not parts:
        return True
    norm_claim = normalize(claim)
    return any(normalize(p) in norm_claim for p in parts)


def year_in_claim(actual_year: str | int | None, claim: str) -> bool:
    if actual_year is None:
        return True
    y = str(actual_year)
    if not y or not y.isdigit():
        return True
    # Allow off-by-one (preprint year vs published year).
    yi = int(y)
    return any(str(yi + d) in claim for d in (-1, 0, 1))


def journal_close_match(actual: str, claim: str) -> bool:
    if not actual:
        return True
    a = normalize(actual)
    c = normalize(claim)
    # Match if any 4+ char journal token appears in the claim string,
    # OR a known abbreviation maps in. Simple and forgiving.
    tokens = [t for t in a.split() if len(t) >= 4]
    return any(t in c for t in tokens) if tokens else True
