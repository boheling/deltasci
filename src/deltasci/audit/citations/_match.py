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


# Citation scaffolding that does not count as asserted bibliographic metadata.
_CITE_SCAFFOLD = frozenset(
    {"et", "al", "pmid", "doi", "arxiv", "pubmed", "preprint", "https", "http", "www", "org", "com", "abs"}
)
_YEAR_RE = re.compile(r"\b(?:19|20)\d{2}\b")


def claim_asserts_metadata(claim_source: str, identifier) -> bool:
    """True if the claim carries bibliographic metadata beyond the bare identifier.

    A bare identifier ("PMID 35562209", "arXiv:2502.14297") asserts nothing to
    cross-check, so a successful fetch should verify on *existence* rather than
    manufacture an author/year "mismatch" against metadata the claim never stated.
    A real cite ("Zhou Y 2022, Nature Comms — Tumor macrophages…") asserts plenty and
    still flows through the full per-field checks (preserving the BioIntel catch).
    """

    norm = normalize(claim_source)
    for raw in (identifier.value, getattr(identifier, "raw", "")):
        for tok in normalize(raw).split():
            if tok:
                norm = re.sub(rf"\b{re.escape(tok)}\b", " ", norm)
    content = [t for t in norm.split() if len(t) >= 4 and t not in _CITE_SCAFFOLD]
    # Check the year on the *stripped* text so a year-like substring inside the identifier
    # itself (e.g. the DOI 10.1109/CVPR.2016.90) isn't mistaken for an asserted year.
    return bool(content) or bool(_YEAR_RE.search(norm))


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
    name_tokens = [normalize(p) for p in re.split(r"[,\s]+", first) if normalize(p)]
    if not name_tokens:
        return True
    # Match on the family name (the first OR last token — covers both "Gu SQ" and
    # "Si Qian Gu" formats) regardless of length, plus any distinctive 4+ char token.
    # Whole-word match against the claim's tokens. This stops short family names like
    # "Gu" from being dropped (the len>=4 filter used to cause false mismatches).
    candidates = {name_tokens[0], name_tokens[-1]}
    candidates.update(t for t in name_tokens if len(t) >= 4)
    claim_tokens = set(normalize(claim).split())
    return any(c in claim_tokens for c in candidates if c)


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
