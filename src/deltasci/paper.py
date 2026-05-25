"""Whole-paper citation verification.

Real papers cite by number in the body (``…drives metastasis [12].``) with the actual
reference in a bibliography at the bottom — so a pasted paragraph alone has only `[12]`,
nothing to resolve. This module ingests the *whole* document, links each in-text marker
to its reference, resolves that reference to a real record (embedded DOI/PMID/arXiv, or a
Crossref title lookup), and runs the audit engine per citation *in the context of the
sentence that cites it*.

Deterministic-first: numbered references + ``[n]`` markers need no LLM and no key beyond
the record lookups. An optional LLM fallback handles messy / author-year bibliographies
when a provider key is configured (see `paper_llm.py`).
"""

from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

from deltasci.audit.base import AuditFinding
from deltasci.audit.cache import AuditCache
from deltasci.audit.citations._match import normalize
from deltasci.audit.extractor import Identifier, extract_identifiers
from deltasci.audit.http import HTTPError, get_json
from deltasci.audit.intake import Claim
from deltasci.audit.report_md import verdict as finding_verdict
from deltasci.verify import verify_claims

CROSSREF_URL = "https://api.crossref.org/works"

# Most-severe-first; an unresolved reference (no findings) is reported UNVERIFIABLE.
_SEVERITY = ["FABRICATED", "METADATA-MISMATCH", "UNSUPPORTED", "UNVERIFIABLE", "SKIPPED", "PASS"]

# --- reference-section detection ----------------------------------------------------
_REF_HEADING_RE = re.compile(
    r"(?im)^[ \t]*\(?\d{0,2}\)?[ \t]*"
    r"(references|bibliography|works cited|literature cited|references and notes)"
    r"[ \t]*:?[ \t]*$"
)

# A numbered reference entry start: "[12]", "12.", "12)" at the beginning of a line.
_REF_ENTRY_RE = re.compile(r"(?m)^[ \t]*(?:\[(\d{1,3})\]|(\d{1,3})[.)])[ \t]+")

# In-text citation markers: [12], [1, 3], [1-4], [1–4, 7].
_CITE_MARKER_RE = re.compile(r"\[(\d+(?:\s*[,–-]\s*\d+)*)\]")

_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z(\[\"'])")

# Reference markers are small integers; this cap keeps "[2018-2021]" (a year range) and
# other large bracketed numbers from being mistaken for citation numbers.
_MAX_REF_NUMBER = 300

# A real bibliography entry carries a publication year; this filters out numbered list
# items in appendices (rubrics, prompt steps) that aren't citations.
_REF_YEAR_RE = re.compile(r"\b(?:19|20)\d{2}\b")


def _is_reference_like(raw: str, identifiers: list[Identifier]) -> bool:
    return bool(identifiers) or bool(_REF_YEAR_RE.search(raw))


@dataclass
class Reference:
    """One bibliography entry."""

    number: int | None
    raw: str
    identifiers: list[Identifier] = field(default_factory=list)
    resolved_doi: str | None = None
    resolved_title: str | None = None

    @property
    def source_string(self) -> str:
        """What to hand the audit engine as the citation `source`.

        Prefer an embedded identifier (the raw text carries it and the extractor will
        find it); otherwise a Crossref-resolved DOI; otherwise the raw text (the engine
        will report it unverifiable, which is the honest outcome)."""

        if self.identifiers:
            return self.raw
        if self.resolved_doi:
            return f"doi:{self.resolved_doi}"
        return self.raw


@dataclass
class InTextCite:
    """A sentence in the body and the reference numbers it cites."""

    numbers: list[int]
    sentence: str


def split_body_and_references(text: str) -> tuple[str, str]:
    """Split a document into (body, references_text) at the last bibliography heading."""

    matches = list(_REF_HEADING_RE.finditer(text))
    if not matches:
        return text, ""
    last = matches[-1]
    return text[: last.start()], text[last.end() :]


def parse_numbered_references(refs_text: str) -> list[Reference]:
    """Parse a numbered bibliography into Reference entries (whitespace collapsed)."""

    matches = list(_REF_ENTRY_RE.finditer(refs_text))
    refs: list[Reference] = []
    for i, m in enumerate(matches):
        num = int(m.group(1) or m.group(2))
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(refs_text)
        raw = re.sub(r"\s+", " ", refs_text[start:end]).strip()
        if not raw:
            continue
        ids = extract_identifiers(raw)
        if _is_reference_like(raw, ids):  # skip appendix list-items that aren't citations
            refs.append(Reference(number=num, raw=raw, identifiers=ids))
    return refs


def extract_identifier_references(refs_text: str) -> list[Reference]:
    """Fallback for author-year / unparseable bibliographies with no usable LLM: pull every
    verifiable identifier (DOI / PMID / arXiv) out of the references section and make one
    Reference per identifier. Verifies that each cited work *exists*, even when the entries
    can't be segmented into numbered records.
    """

    refs: list[Reference] = []
    seen: set[tuple[str, str]] = set()
    for ident in extract_identifiers(refs_text):
        key = (ident.kind, ident.value.lower())
        if key in seen:
            continue
        seen.add(key)
        refs.append(Reference(number=len(refs) + 1, raw=ident.raw, identifiers=[ident]))
    return refs


def _expand_marker(group: str) -> list[int]:
    """'1, 3-5' -> [1, 3, 4, 5]."""

    nums: set[int] = set()
    for part in re.split(r"\s*,\s*", group):
        rng = re.split(r"\s*[–-]\s*", part)
        if len(rng) == 2 and rng[0].isdigit() and rng[1].isdigit():
            lo, hi = int(rng[0]), int(rng[1])
            if 0 < hi - lo < 100 and hi <= _MAX_REF_NUMBER:  # not a year range
                nums.update(range(lo, hi + 1))
        elif part.strip().isdigit():
            n = int(part.strip())
            if 0 < n <= _MAX_REF_NUMBER:
                nums.add(n)
    return sorted(nums)


def _sentences(text: str) -> list[str]:
    # PDF text wraps mid-sentence, so flatten all whitespace into single spaces BEFORE
    # splitting on sentence boundaries — otherwise a citation marker gets severed from
    # the sentence it belongs to.
    flat = re.sub(r"\s+", " ", text).strip()
    if not flat:
        return []
    return [s.strip() for s in _SENTENCE_RE.split(flat) if s.strip()]


def find_in_text_cites(body: str) -> list[InTextCite]:
    """Find every sentence carrying a numeric citation marker, with the cited numbers."""

    cites: list[InTextCite] = []
    for sent in _sentences(body):
        nums: set[int] = set()
        for m in _CITE_MARKER_RE.finditer(sent):
            nums.update(_expand_marker(m.group(1)))
        if nums:
            cites.append(InTextCite(numbers=sorted(nums), sentence=sent))
    return cites


def claim_for_reference(number: int, cites: list[InTextCite]) -> str:
    """All in-text sentences that cite reference `number`, joined — the claim context."""

    return " ".join(c.sentence for c in cites if number in c.numbers).strip()


def looks_numbered(references: list[Reference], cites: list[InTextCite]) -> bool:
    """Heuristic: did deterministic numbered parsing find a *genuine* numbered bibliography?

    A real numbered bibliography is a sequence [1], [2], [3], … — unique, starting at 1, and
    largely sequential. Appendix numbered-lists (rubrics, prompt steps) instead repeat and
    restart (e.g., 1,2,3,1,2…) — so requiring sequence rejects them and the caller falls back
    to the LLM or identifier-extraction path. When False, the numbered parse is not trusted.
    """

    nums = [r.number for r in references if r.number is not None]
    if len(nums) < 3:
        return False
    uniq = sorted(set(nums))
    if uniq[0] != 1:  # a real bibliography starts at [1]
        return False
    if len(uniq) < 0.8 * len(nums):  # too many duplicate numbers → not a bibliography
        return False
    # numbers should be reasonably dense (few gaps), i.e. ~1..N
    return uniq[-1] <= 1.5 * len(uniq)


def _title_overlaps(title: str, ref_raw: str, min_overlap: float = 0.6) -> bool:
    """True if most of `title`'s content words appear in the reference text.

    Guards against Crossref confidently returning an unrelated top hit: we only accept
    a resolution when the candidate title is clearly present in the bibliography entry.
    """

    title_tokens = {w for w in normalize(title).split() if len(w) >= 4}
    if not title_tokens:
        return False
    ref_norm = normalize(ref_raw)
    hits = sum(1 for w in title_tokens if w in ref_norm)
    return hits / len(title_tokens) >= min_overlap


def resolve_reference(ref: Reference, timeout: float = 10.0) -> Reference:
    """Fill in a DOI for a reference that has no embedded identifier, via Crossref.

    Mutates and returns `ref`. No-op if it already carries a PMID/DOI/arXiv id."""

    if ref.identifiers or not ref.raw.strip():
        return ref
    try:
        data = get_json(
            CROSSREF_URL,
            timeout=timeout,
            params={"query.bibliographic": ref.raw[:500], "rows": "1", "mailto": "audit@deltasci.local"},
        )
    except HTTPError:
        return ref
    items = (data.get("message") or {}).get("items") or []
    if not items:
        return ref
    top = items[0]
    title = (top.get("title") or [""])[0] if isinstance(top.get("title"), list) else (top.get("title") or "")
    doi = top.get("DOI")
    if doi and title and _title_overlaps(title, ref.raw):
        ref.resolved_doi = doi
        ref.resolved_title = title
    return ref


def _reference_keys(ref: Reference) -> set[str]:
    keys = {i.value.lower() for i in ref.identifiers}
    if ref.resolved_doi:
        keys.add(ref.resolved_doi.lower())
    return keys


def _finding_identifiers(f: AuditFinding) -> set[str]:
    """All identifier values a finding carries (a DataCite arXiv finding has both an
    'arxiv' id and a '10.48550/arXiv…' DOI), so grouping matches on any of them."""

    fm = f.fetched_metadata
    vals = {str(fm[k]).lower() for k in ("pmid", "doi", "arxiv", "id", "accession", "repo") if fm.get(k)}
    if not vals:
        vals = {i.value.lower() for i in extract_identifiers(f.target_summary)}
    return vals


def _overall_verdict(findings: list[AuditFinding]) -> str:
    verds = {finding_verdict(f) for f in findings}
    for v in _SEVERITY:
        if v in verds:
            return v
    return "UNVERIFIABLE"  # no findings → couldn't resolve/verify


@dataclass
class CitationResult:
    """Per-reference verification outcome, with the in-text claim it was cited for."""

    number: int | None
    reference_raw: str
    resolved_title: str | None
    claim: str
    verdict: str
    findings: list[AuditFinding]
    note: str = ""


@dataclass
class PaperReport:
    references: list[Reference]
    cites: list[InTextCite]
    results: list[CitationResult]
    used_llm_fallback: bool = False

    def counts(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for r in self.results:
            out[r.verdict] = out.get(r.verdict, 0) + 1
        return out


def verify_paper(
    text: str,
    *,
    check_support: bool = True,
    resolve: bool = True,
    cache: AuditCache | None = None,
    max_workers: int = 8,
    max_references: int | None = None,
    llm=None,
) -> PaperReport:
    """Parse a whole paper, resolve every reference, and verify each citation in context.

    `max_references` optionally caps how many references are actually verified (in document
    order) — useful when a large bibliography would otherwise take minutes against free,
    rate-limited APIs. Capped references are still listed, marked 'not checked'. Default
    (None) verifies every reference.

    `llm` (an `LLMAdapter`) enables a fallback: when deterministic numbered-reference
    parsing comes up short (e.g., author-year citations), the LLM structures the citations
    into (claim, source) pairs — verification of each still happens deterministically.
    """

    body, refs_text = split_body_and_references(text)
    references = parse_numbered_references(refs_text)
    cites = find_in_text_cites(body)
    used_llm = False
    claim_text_by_index: dict[int, str] | None = None

    if not looks_numbered(references, cites):
        # Numbered parsing didn't find a real bibliography (e.g., an author-year paper).
        if llm is not None:
            from deltasci.paper_llm import llm_extract_citations

            llm_claims = llm_extract_citations(text, llm)
            if llm_claims:
                used_llm = True
                references = [
                    Reference(number=i + 1, raw=c.source, identifiers=extract_identifiers(c.source))
                    for i, c in enumerate(llm_claims)
                ]
                claim_text_by_index = {i: c.claim for i, c in enumerate(llm_claims)}
        if not used_llm:
            # Deterministic, key-free fallback: verify every identifier in the bibliography.
            id_refs = extract_identifier_references(refs_text)
            if len(id_refs) > len(references):
                references = id_refs

    to_check = references[:max_references] if max_references else references
    capped = references[len(to_check) :]

    # Resolve references lacking an embedded identifier (concurrently).
    if resolve and to_check:
        unresolved = [r for r in to_check if not r.identifiers]
        if unresolved:
            with ThreadPoolExecutor(max_workers=max_workers) as pool:
                list(pool.map(resolve_reference, unresolved))

    # One Claim per reference: source = its identifier/DOI; claim text = the in-text
    # sentence(s) that cite it (so the support check runs against the real claim context),
    # falling back to the reference's own text when it isn't cited inline.
    claims: list[Claim] = []
    for idx, ref in enumerate(to_check):
        if claim_text_by_index is not None:
            context = claim_text_by_index.get(idx, "")
        else:
            context = claim_for_reference(ref.number, cites) if ref.number is not None else ""
        claims.append(Claim(claim=(context or ref.raw), source=ref.source_string))

    report = verify_claims(claims, check_support=check_support, cache=cache, max_workers=max_workers)

    # Group findings back onto references by identifier.
    results: list[CitationResult] = []
    for ref, claim in zip(to_check, claims):
        keys = _reference_keys(ref)
        findings = [f for f in report.findings if _finding_identifiers(f) & keys] if keys else []
        results.append(
            CitationResult(
                number=ref.number,
                reference_raw=ref.raw,
                resolved_title=ref.resolved_title,
                claim=claim.claim,
                verdict=_overall_verdict(findings),
                findings=findings,
            )
        )
    for ref in capped:
        results.append(
            CitationResult(
                number=ref.number,
                reference_raw=ref.raw,
                resolved_title=None,
                claim="",
                verdict="SKIPPED",
                findings=[],
                note="not checked (reference cap)",
            )
        )

    return PaperReport(references=references, cites=cites, results=results, used_llm_fallback=used_llm)


def extract_pdf_text(path: str) -> str:
    """Extract text from a PDF via PyMuPDF (optional `deltasci[pdf]` extra)."""

    try:
        import fitz  # PyMuPDF
    except ImportError:
        try:
            import pymupdf as fitz  # newer import name
        except ImportError as exc:
            raise RuntimeError(
                "PDF support requires PyMuPDF. Install it with:  pip install 'deltasci[pdf]'"
            ) from exc
    doc = fitz.open(path)
    try:
        return "\n".join(page.get_text() for page in doc)
    finally:
        doc.close()


_VERDICT_SYMBOL = {
    "PASS": "✓",
    "FABRICATED": "✗",
    "METADATA-MISMATCH": "✗",
    "UNSUPPORTED": "⚠",
    "UNVERIFIABLE": "⊘",
    "SKIPPED": "…",
}


def render_paper_terminal(report: PaperReport, *, show_passed: bool = True) -> str:
    """Per-reference terminal report, most-severe first."""

    counts = report.counts()
    failed = sum(counts.get(v, 0) for v in ("FABRICATED", "METADATA-MISMATCH", "UNSUPPORTED"))
    order = {v: i for i, v in enumerate(_SEVERITY)}
    lines = [
        f"Paper verification: {len(report.references)} references · "
        f"{failed} failed audit{'' if failed == 1 else 's'}"
        + ("  (LLM fallback used)" if report.used_llm_fallback else ""),
        "  " + "  ".join(f"{_VERDICT_SYMBOL.get(v, '?')} {v}: {n}" for v, n in sorted(counts.items(), key=lambda kv: order.get(kv[0], 99))),
        "",
    ]
    for r in sorted(report.results, key=lambda r: order.get(r.verdict, 99)):
        if r.verdict == "PASS" and not show_passed:
            continue
        sym = _VERDICT_SYMBOL.get(r.verdict, "?")
        num = f"[{r.number}] " if r.number is not None else ""
        title = r.resolved_title or r.reference_raw[:90]
        lines.append(f"{sym} {r.verdict}  {num}{title}")
        seen: set[str] = set()
        for f in r.findings:
            for reason in f.mismatch_reasons[:1]:
                if reason not in seen:
                    seen.add(reason)
                    lines.append(f"      → {reason}")
    return "\n".join(lines).rstrip() + "\n"


def paper_payload(report: PaperReport) -> dict:
    """JSON-ready summary for the CLI / web / MCP surfaces."""

    return {
        "counts": report.counts(),
        "reference_count": len(report.references),
        "used_llm_fallback": report.used_llm_fallback,
        "citations": [
            {
                "number": r.number,
                "verdict": r.verdict,
                "claim": r.claim,
                "reference": r.reference_raw,
                "resolved_title": r.resolved_title,
                "note": r.note,
                "findings": [{**f.model_dump(), "verdict": finding_verdict(f)} for f in r.findings],
            }
            for r in report.results
        ],
    }


__all__ = [
    "CitationResult",
    "InTextCite",
    "PaperReport",
    "Reference",
    "claim_for_reference",
    "extract_identifier_references",
    "extract_pdf_text",
    "find_in_text_cites",
    "looks_numbered",
    "paper_payload",
    "parse_numbered_references",
    "render_paper_terminal",
    "resolve_reference",
    "split_body_and_references",
    "verify_paper",
]
