"""Turn arbitrary input into auditable claims.

The audit runner ([`MultiLayerAuditor`][deltasci.audit.runner.MultiLayerAuditor])
only needs objects exposing two attributes: ``.claim`` and ``.source``. This module
is the bridge from "any LLM-generated scientific text" to that — so the verifier can
run on a pasted related-work section, a JSON list of claims, or a `.bib` file, not just
a full DeltaScience run.

Four intake modes:

- **tagged**   — DeltaScience ``[CLAIM ... source="..."]...[/CLAIM]`` text
- **text**     — untagged prose: split into sentences, keep the ones that cite something
- **records**  — JSON ``[{"claim": "...", "source": "..."}, ...]``
- **bibtex**   — a ``.bib`` reference list (verify the references resolve)

Keeping this module dependency-free (no import from ``deltasci.hypothesis`` or
``deltasci.grounding``) is deliberate: it keeps the whole ``audit/`` package
self-contained and cleanly extractable into a standalone ``deltasci-verify`` package.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Iterable, Literal

from deltasci.audit.extractor import extract_identifiers

Format = Literal["auto", "tagged", "text", "records", "bibtex"]


@dataclass(frozen=True)
class Claim:
    """A minimal auditable unit: a statement plus the source string that should back it.

    Satisfies the ``.claim`` / ``.source`` duck-type the audit runner consumes, so it can
    stand in for an ``EvidenceItem`` without dragging in the hypothesis schema.
    """

    claim: str
    source: str


# --- tagged mode: DeltaScience [CLAIM ... source="..."] tags --------------------------
# Inlined (not imported from deltasci.grounding) to keep audit/ self-contained.
_CLAIM_TAG_RE = re.compile(r"\[CLAIM\s+([^\]]*?)\](.*?)\[/CLAIM\]", re.DOTALL)
_ATTR_RE = re.compile(r'(\w+)\s*=\s*(?:"([^"]*)"|(\S+))')

# --- untagged mode: sentence segmentation --------------------------------------------
# Split on sentence-ending punctuation followed by whitespace + a likely sentence start.
_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z(\[\"'])")

# --- bibtex mode ---------------------------------------------------------------------
_BIB_ENTRY_RE = re.compile(r"@\w+\s*\{\s*([^,]*),(.*?)\n\s*\}", re.DOTALL)
_BIB_FIELD_RE = re.compile(r"(\w+)\s*=\s*[{\"]([^}\"]*)[}\"]", re.DOTALL)


def _parse_attrs(attr_str: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for m in _ATTR_RE.finditer(attr_str or ""):
        key = m.group(1)
        val = m.group(2) if m.group(2) is not None else (m.group(3) or "")
        out[key] = val
    return out


def from_tagged_text(text: str) -> list[Claim]:
    """Pull claims out of DeltaScience ``[CLAIM ... source="..."]`` tags."""

    claims: list[Claim] = []
    for m in _CLAIM_TAG_RE.finditer(text):
        attrs = _parse_attrs(m.group(1))
        body = m.group(2).strip()
        source = attrs.get("source", "").strip()
        if body:
            claims.append(Claim(claim=body, source=source))
    return claims


def _segments(text: str) -> Iterable[str]:
    """Yield candidate claim segments: split on newlines, then on sentence boundaries."""

    for line in text.replace("\r\n", "\n").split("\n"):
        line = line.strip()
        if not line:
            continue
        # Strip common bullet / list-marker prefixes so they don't pollute the claim text.
        line = re.sub(r"^\s*(?:[-*•]|\d+[.)])\s+", "", line)
        for sent in _SENTENCE_RE.split(line):
            sent = sent.strip()
            if sent:
                yield sent


def from_text(text: str) -> list[Claim]:
    """Untagged prose. Keep each sentence that cites a verifiable identifier.

    The cited identifier(s) become the claim's ``source`` (so the metadata verifiers
    fire) while the full sentence is the ``claim`` (so the support/quote checks can
    compare it against the fetched abstract). Sentences with no verifiable identifier
    are not auditable and are skipped — see :func:`split_stats` to count them.
    """

    claims: list[Claim] = []
    for sent in _segments(text):
        idents = extract_identifiers(sent)
        if not idents:
            continue
        source = " ".join(dict.fromkeys(i.raw for i in idents))  # dedup, preserve order
        claims.append(Claim(claim=sent, source=source))
    return claims


def split_stats(text: str) -> tuple[int, int]:
    """Return (cited_sentences, uncited_sentences) for honest reporting in `verify`."""

    cited = uncited = 0
    for sent in _segments(text):
        if extract_identifiers(sent):
            cited += 1
        else:
            uncited += 1
    return cited, uncited


def from_records(data: str | list) -> list[Claim]:
    """JSON list of ``{"claim": ..., "source": ...}`` objects (or a pre-parsed list)."""

    records = json.loads(data) if isinstance(data, str) else data
    if not isinstance(records, list):
        raise ValueError("records input must be a JSON array of {claim, source} objects")
    claims: list[Claim] = []
    for i, rec in enumerate(records):
        if not isinstance(rec, dict) or "claim" not in rec:
            raise ValueError(f"record #{i} must be an object with at least a 'claim' field")
        claims.append(Claim(claim=str(rec["claim"]).strip(), source=str(rec.get("source", "")).strip()))
    return claims


def from_bibtex(text: str) -> list[Claim]:
    """Minimal `.bib` parser: one claim per entry, citing its DOI/title/author/year."""

    claims: list[Claim] = []
    for m in _BIB_ENTRY_RE.finditer(text):
        fields = {k.lower(): v.strip() for k, v in _BIB_FIELD_RE.findall(m.group(2))}
        title = fields.get("title", "").strip()
        source_bits = [fields[k] for k in ("doi", "title", "author", "year", "journal") if fields.get(k)]
        source = ", ".join(source_bits)
        if source:
            claims.append(Claim(claim=title or m.group(1).strip(), source=source))
    return claims


def detect_format(text: str) -> Format:
    """Best-effort format sniffing for ``--format auto``."""

    stripped = text.lstrip()
    if "[CLAIM" in text:
        return "tagged"
    if stripped[:1] in "[{":
        return "records"
    if re.match(r"@\w+\s*\{", stripped):
        return "bibtex"
    return "text"


def claims_from_source(text: str, *, fmt: Format = "auto") -> list[Claim]:
    """Dispatch to the right extractor. ``fmt='auto'`` sniffs the input."""

    if fmt == "auto":
        fmt = detect_format(text)
    if fmt == "tagged":
        return from_tagged_text(text)
    if fmt == "records":
        return from_records(text)
    if fmt == "bibtex":
        return from_bibtex(text)
    if fmt == "text":
        return from_text(text)
    raise ValueError(f"unknown intake format: {fmt!r}")


__all__ = [
    "Claim",
    "Format",
    "claims_from_source",
    "detect_format",
    "from_bibtex",
    "from_records",
    "from_tagged_text",
    "from_text",
    "split_stats",
]
