"""Pull verifiable identifiers (PMID, DOI, arXiv, GitHub repo, etc.) out of a free-text source string.

This is the bridge between LLM-emitted CLAIM source strings and the API verifiers.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

IdentifierKind = Literal[
    "pmid",
    "doi",
    "arxiv",
    "github",
    "huggingface",
    "geo",       # NCBI GEO accession
    "sra",       # NCBI SRA accession
    "zenodo",
]


@dataclass(frozen=True)
class Identifier:
    kind: IdentifierKind
    value: str  # canonical form (e.g., "35562209" for pmid; "10.1038/nature01" for doi)
    raw: str    # what we matched in the source string


PMID_RE = re.compile(r"PMID[:\s]*(\d{6,9})", re.IGNORECASE)
PMID_BARE_RE = re.compile(r"\bpubmed[:/](\d{6,9})", re.IGNORECASE)
DOI_RE = re.compile(r"\b(10\.\d{4,9}/[^\s\"<>)\]]+)", re.IGNORECASE)
ARXIV_RE = re.compile(
    # "arXiv:2303.08774", "arXiv 2303.08774", and the URL form "arxiv.org/abs/2303.08774"
    r"\barxiv(?:\.org/(?:abs|pdf)/|[:\s/]*)"
    r"(\d{4}\.\d{4,5}(?:v\d+)?|[a-z\-]+/\d{7}(?:v\d+)?)",
    re.IGNORECASE,
)
GITHUB_RE = re.compile(
    r"\bgithub\.com[/:]([a-z0-9][a-z0-9\-_.]*?/[a-z0-9][a-z0-9\-_.]*?)(?=[\s\"<>)\]/]|$)",
    re.IGNORECASE,
)
HUGGINGFACE_RE = re.compile(
    r"\bhuggingface\.co/([a-z0-9][a-z0-9\-_.]*?/[a-z0-9][a-z0-9\-_.]*?)(?=[\s\"<>)\]/]|$)",
    re.IGNORECASE,
)
GEO_RE = re.compile(r"\b(GSE\d{3,7}|GDS\d{3,6}|GPL\d{3,6}|GSM\d{6,9})\b")
SRA_RE = re.compile(r"\b(SRP\d{6,9}|SRR\d{6,9}|SRX\d{6,9}|SRS\d{6,9})\b")
ZENODO_RE = re.compile(r"\bzenodo\.org/record/(\d{4,9})", re.IGNORECASE)


def _strip_doi_trailing_punct(doi: str) -> str:
    # DOIs frequently get trailing periods/commas swept in by the regex.
    while doi and doi[-1] in ".,;":
        doi = doi[:-1]
    return doi


def extract_identifiers(source_string: str) -> list[Identifier]:
    """Find all verifiable identifiers in a free-text source string.

    Multiple identifiers may exist in one string (e.g., "Smith 2020, Nature, PMID 12345, DOI 10.1038/x").
    Order: PMID > DOI > arXiv > repos > datasets. Caller decides which to act on.
    """

    out: list[Identifier] = []
    seen: set[tuple[str, str]] = set()

    def add(kind: IdentifierKind, value: str, raw: str) -> None:
        key = (kind, value.lower())
        if key in seen:
            return
        seen.add(key)
        out.append(Identifier(kind=kind, value=value, raw=raw))

    for m in PMID_RE.finditer(source_string):
        add("pmid", m.group(1), m.group(0))
    for m in PMID_BARE_RE.finditer(source_string):
        add("pmid", m.group(1), m.group(0))
    for m in DOI_RE.finditer(source_string):
        doi = _strip_doi_trailing_punct(m.group(1))
        add("doi", doi, m.group(0))
    for m in ARXIV_RE.finditer(source_string):
        add("arxiv", m.group(1), m.group(0))
    for m in GITHUB_RE.finditer(source_string):
        add("github", m.group(1), m.group(0))
    for m in HUGGINGFACE_RE.finditer(source_string):
        add("huggingface", m.group(1), m.group(0))
    for m in GEO_RE.finditer(source_string):
        add("geo", m.group(1), m.group(0))
    for m in SRA_RE.finditer(source_string):
        add("sra", m.group(1), m.group(0))
    for m in ZENODO_RE.finditer(source_string):
        add("zenodo", m.group(1), m.group(0))

    return out
