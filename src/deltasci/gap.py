"""Gap analysis — the grounded "what's missing / how is this different?" component.

`scan` answers *what already exists* near an idea. `gap` reads that retrieval and asks the
follow-up a grant reviewer or an ideator actually cares about: **is this space crowded, or
is there white space?** It does so deterministically from the real prior art —

  * **Saturation** — how strong and how many the closest real works are. The honest signal
    a keyless tool can give: it measures *retrieval saturation*, not conceptual novelty.
    CROWDED → don't reinvent, read these. CONTESTED → adjacent work exists, find your angle.
    OPEN → little direct prior art (which may mean novel, or just niche/vague terms).
  * **Distinguishing terms** — concepts in the idea that *none* of the closest works mention.
    Grounded candidates for where the angle is unique (or where the terminology diverges).

An opt-in LLM narrative can articulate the gap in prose, but it is **commentary only**: it
is fed the real retrieved works and told to ground every claim in them and never invent a
paper. The trust path stays the deterministic retrieval `scan` already produced — no model
memory is ever consulted for what exists.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from deltasci.audit.support import salient_terms
from deltasci.scan import ScanHit, ScanReport, scan

# Classification thresholds over the top hit's term-overlap score (see scan._score).
CLOSE_OVERLAP = 0.45  # a hit at/above this is "close" prior art
SATURATED_OVERLAP = 0.60  # top hit this similar → the space is crowded
CONTESTED_OVERLAP = 0.40  # some genuinely adjacent work exists
THIN_EVIDENCE = 3  # fewer hits than this → low confidence in the verdict

# The scholarly corpora. An "open / white space" claim is an assertion of *absence*, and is
# only trustworthy if these actually answered — a rate-limited PubMed might index exactly the
# papers that close the gap. (GitHub is excluded: it's repos, not the literature, so its
# failing doesn't undermine a claim about whether the *research* exists.)
SCHOLARLY = frozenset({"openalex", "arxiv", "pubmed"})

CROWDED = "CROWDED"
CONTESTED = "CONTESTED"
OPEN = "OPEN"
INCONCLUSIVE = "INCONCLUSIVE"

_LABELS = {
    CROWDED: "Crowded — strong direct prior art exists; read it before building",
    CONTESTED: "Contested — adjacent work exists; carve a distinguishing angle",
    OPEN: "Open — little direct prior art (confirm your terms are specific, not just niche)",
    INCONCLUSIVE: "Inconclusive — a source didn't respond, so the space can't be called open; re-run before trusting this",
}


@dataclass
class GapReport:
    query: str
    terms: list[str]
    classification: str  # CROWDED | CONTESTED | OPEN
    label: str
    top_overlap: float
    n_close: int
    covered_terms: list[str]  # idea terms the closest works already address
    novel_terms: list[str]  # idea terms no close work mentions → distinguishing candidates
    scan: ScanReport
    thin: bool = False  # too few hits to be confident
    retrieval_ok: bool = True  # every scholarly corpus we tried actually answered
    failed_sources: list[str] = field(default_factory=list)  # corpora that didn't respond
    narrative: str | None = None  # opt-in LLM prose, grounded in `scan.hits`


def _classify(hits: list[ScanHit], retrieval_ok: bool) -> tuple[str, float, int]:
    """Presence verdicts (CROWDED/CONTESTED) are robust to partial retrieval — you can't
    un-find a close match. The absence verdict (OPEN) is not: if a scholarly corpus failed,
    we cannot honestly call the space open, so it becomes INCONCLUSIVE instead."""

    if not hits:
        return (OPEN if retrieval_ok else INCONCLUSIVE), 0.0, 0
    top = hits[0].score
    n_close = sum(1 for h in hits if h.score >= CLOSE_OVERLAP)
    if top >= SATURATED_OVERLAP and n_close >= 2:
        return CROWDED, top, n_close
    if top >= CONTESTED_OVERLAP:
        return CONTESTED, top, n_close
    return (OPEN if retrieval_ok else INCONCLUSIVE), top, n_close


def analyze_gap(
    text: str,
    *,
    sources: list[str] | None = None,
    limit: int = 10,
    scan_report: ScanReport | None = None,
    llm: object | None = None,
    **scan_kwargs: object,
) -> GapReport:
    """Classify the white space around `text` from real prior art.

    Pass a precomputed `scan_report` (the workflow layer does, to avoid re-querying);
    otherwise a scan is run. `llm`, if given, adds a grounded prose narrative.
    """

    report = scan_report if scan_report is not None else scan(text, sources=sources, limit=limit, **scan_kwargs)  # type: ignore[arg-type]
    hits = report.hits

    # Retrieval is trustworthy enough to assert *absence* only if at least one scholarly
    # corpus was queried AND none of the scholarly corpora we tried failed.
    failed_scholarly = sorted(set(report.failed_sources) & SCHOLARLY)
    attempted_scholarly = (set(report.ok_sources) | set(report.failed_sources)) & SCHOLARLY
    retrieval_ok = bool(attempted_scholarly) and not failed_scholarly

    classification, top_overlap, n_close = _classify(hits, retrieval_ok)

    idea_terms = report.terms or sorted(salient_terms(text))
    hit_term_union: set[str] = set()
    for h in hits:
        hit_term_union |= salient_terms(f"{h.title} {h.snippet}")
    covered = [t for t in idea_terms if t in hit_term_union]
    novel = [t for t in idea_terms if t not in hit_term_union]

    gap = GapReport(
        query=report.query,
        terms=idea_terms,
        classification=classification,
        label=_LABELS[classification],
        top_overlap=top_overlap,
        n_close=n_close,
        covered_terms=covered,
        novel_terms=novel,
        scan=report,
        thin=len(hits) < THIN_EVIDENCE,
        retrieval_ok=retrieval_ok,
        failed_sources=failed_scholarly,
    )

    if llm is not None and hits:
        try:
            gap.narrative = _llm_gap_narrative(text, hits, classification, llm)
        except Exception:  # noqa: BLE001 - narrative is optional commentary; never sink the report
            gap.narrative = None
    return gap


# --- opt-in LLM narrative (commentary only; grounded in retrieved works) --------------
_GAP_SYSTEM = (
    "You are a research strategist assessing the novelty of a proposed idea. You are given "
    "the idea and the closest REAL prior works retrieved for it. Ground every statement in "
    "those listed works, referring to them by author and year. You NEVER invent a paper, "
    "author, or finding: if a point is not supported by the listed works, do not make it. "
    "If the listed works already cover the idea, say so plainly."
)

_GAP_PROMPT = """\
PROPOSED IDEA:
{idea}

CLOSEST PRIOR WORKS (retrieved, real):
{works}

In 2-4 sentences, state where the genuine gap is: what these works already cover, and what
specific dimension of the idea appears unaddressed by them. Be concrete and grounded; do not
speculate beyond the listed works. End with one line: "Distinguishing angle: <one phrase>".
"""


def _format_works(hits: list[ScanHit], k: int = 6) -> str:
    lines = []
    for i, h in enumerate(hits[:k], 1):
        who = ", ".join(h.authors[:2]) or h.source
        meta = " · ".join(x for x in [who, h.year, h.venue] if x)
        snip = (h.snippet[:200] + "…") if len(h.snippet) > 200 else h.snippet
        lines.append(f"{i}. {h.title} ({meta})" + (f"\n   {snip}" if snip else ""))
    return "\n".join(lines)


def _llm_gap_narrative(text: str, hits: list[ScanHit], classification: str, llm: object) -> str:
    from deltasci.llm.base import Message  # local import: LLM is optional

    prompt = _GAP_PROMPT.format(idea=text.strip()[:2000], works=_format_works(hits))
    raw = llm.complete(system=_GAP_SYSTEM, messages=[Message(role="user", content=prompt)], max_tokens=400)  # type: ignore[attr-defined]
    return raw.strip()


# --- rendering ------------------------------------------------------------------------
def render_gap_terminal(report: GapReport) -> str:
    lines = [
        f"Gap analysis · {report.classification}",
        f"  {report.label}",
        f"  closest-work overlap: {report.top_overlap:.0%}   close works: {report.n_close}   "
        f"retrieved: {len(report.scan.hits)}",
    ]
    if report.failed_sources:
        lines.append(
            f"  ⚠ incomplete coverage — no response from: {', '.join(report.failed_sources)}. "
            + ("Verdict held back from 'open' until you re-run." if report.classification == INCONCLUSIVE
               else "A close match was still found, so the verdict stands.")
        )
    elif report.thin and report.classification in (OPEN, INCONCLUSIVE):
        lines.append("  ⚠ thin evidence (few hits) — treat the verdict as low-confidence.")
    if report.novel_terms:
        lines.append(f"  distinguishing terms (in no close work): {', '.join(report.novel_terms[:8])}")
    if report.covered_terms:
        lines.append(f"  already covered: {', '.join(report.covered_terms[:8])}")
    if report.narrative:
        lines.append("")
        lines.append("  Narrative (LLM, grounded in the works below):")
        for para in report.narrative.splitlines():
            lines.append(f"    {para}")
    lines.append("")
    lines.append("  Closest prior art:")
    for i, h in enumerate(report.scan.hits[:8], 1):
        meta = " · ".join(x for x in [", ".join(h.authors[:2]), h.year, h.venue] if x)
        lines.append(f"  {i:>2}. [{h.source}] {h.title[:90]}  ({h.score:.0%})")
        if meta:
            lines.append(f"        {meta}")
        if h.url:
            lines.append(f"        {h.url}")
    return "\n".join(lines).rstrip() + "\n"


def gap_payload(report: GapReport) -> dict:
    from deltasci.scan import scan_payload

    return {
        "classification": report.classification,
        "label": report.label,
        "query": report.query,
        "terms": report.terms,
        "top_overlap": report.top_overlap,
        "n_close": report.n_close,
        "thin": report.thin,
        "retrieval_ok": report.retrieval_ok,
        "failed_sources": report.failed_sources,
        "covered_terms": report.covered_terms,
        "novel_terms": report.novel_terms,
        "narrative": report.narrative,
        "scan": scan_payload(report.scan),
    }


__all__ = [
    "CONTESTED",
    "CROWDED",
    "INCONCLUSIVE",
    "OPEN",
    "GapReport",
    "analyze_gap",
    "gap_payload",
    "render_gap_terminal",
]
