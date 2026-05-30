"""Write / Ideate — the two *generative* components, grounded in deltasci's evidence.

Unlike verify / scan / gap (which are deterministic and keyless), writing a peer review or
proposing new directions is genuinely a generation task, so these require an LLM. The
discipline that makes them trustworthy is the same one verify enforces: **the model only
ever works from evidence deltasci already produced** — the real citation-audit results and
the real retrieved prior art — and is told never to invent a paper, finding, or identifier.
The model composes; it does not get to decide what is true or what exists.

    review = write_review(paper_text, audit_summary, audit_issues, related_work, llm)
    ideas  = ideate(idea_text, gap_label, novel_terms, related_work, llm)
"""

from __future__ import annotations

from deltasci.scan import ScanHit


def _format_works(hits: list[ScanHit], k: int = 8) -> str:
    if not hits:
        return "(none retrieved)"
    lines = []
    for i, h in enumerate(hits[:k], 1):
        who = ", ".join(h.authors[:2]) or h.source
        meta = " · ".join(x for x in [who, h.year, h.venue] if x)
        lines.append(f"{i}. {h.title} ({meta}) — {h.url}")
    return "\n".join(lines)


def _bullets(items: list[str], empty: str) -> str:
    items = [i for i in items if i.strip()]
    return "\n".join(f"- {i}" for i in items) if items else empty


# --- peer review ---------------------------------------------------------------------
_REVIEW_SYSTEM = (
    "You are a rigorous, fair, and constructive peer reviewer for a top venue. You are given "
    "the paper text, the results of an automated citation audit, and the closest real prior "
    "work retrieved for the paper. Ground your review in this evidence: cite the audit's "
    "findings and the retrieved works by name. You NEVER invent a paper, author, finding, or "
    "identifier, and you never assert the work is wrong without a stated basis. Treat the "
    "citation-audit issues as concrete, checkable facts the authors must address."
)

_REVIEW_PROMPT = """\
PAPER (may be truncated):
{paper}

AUTOMATED CITATION AUDIT:
{audit_summary}
Issues to flag in the review:
{audit_issues}

CLOSEST PRIOR WORK (retrieved, real):
{works}

Write a structured peer review with these sections:
## Summary
## Strengths
## Weaknesses
## Specific concerns (cite the audit issues and any missing comparisons to the prior work above)
## Questions for the authors
## Recommendation (one of: accept / minor revision / major revision / reject, with one line of justification)
Be concrete and grounded. Do not introduce papers or facts not present above.
"""


def write_review(
    paper_text: str,
    audit_summary: str,
    audit_issues: list[str],
    related_work: list[ScanHit],
    llm: object,
    *,
    max_chars: int = 16000,
) -> str:
    """Generate a structured peer review grounded in the audit + retrieved prior art."""

    from deltasci.llm.base import Message  # local import: LLM optional

    prompt = _REVIEW_PROMPT.format(
        paper=paper_text.strip()[:max_chars],
        audit_summary=audit_summary or "(no citations audited)",
        audit_issues=_bullets(audit_issues, "- (no citation issues detected)"),
        works=_format_works(related_work),
    )
    raw = llm.complete(system=_REVIEW_SYSTEM, messages=[Message(role="user", content=prompt)], max_tokens=1600)  # type: ignore[attr-defined]
    return raw.strip()


# --- ideation ------------------------------------------------------------------------
_IDEATE_SYSTEM = (
    "You are a research strategist proposing concrete next directions. You are given an idea, "
    "a deterministic gap verdict, the terms in the idea that no close prior work covers, and "
    "the closest real retrieved works. Ground every proposal in this evidence — anchor each "
    "direction to a retrieved work it extends or differs from, and to the uncovered terms. "
    "You NEVER invent a paper, author, or result. Prefer specific, testable directions over "
    "vague ambition. If the space looks saturated, say so and propose how to differentiate."
)

_IDEATE_PROMPT = """\
IDEA:
{idea}

GAP VERDICT (deterministic): {gap_label}
Terms in the idea that NO close prior work covers (distinguishing candidates):
{novel_terms}

CLOSEST PRIOR WORK (retrieved, real):
{works}

Propose 3-5 concrete, testable research directions. For each:
- **Direction** — one sentence.
- **Why it's open** — anchored to a retrieved work it extends/differs from, or an uncovered term above.
- **First experiment** — the smallest concrete test.
Do not introduce papers or results not present above. End with one line: "Most promising: <#>".
"""


def ideate(
    idea_text: str,
    gap_label: str,
    novel_terms: list[str],
    related_work: list[ScanHit],
    llm: object,
) -> str:
    """Propose grounded next directions from the gap verdict + retrieved prior art."""

    from deltasci.llm.base import Message

    prompt = _IDEATE_PROMPT.format(
        idea=idea_text.strip()[:2000],
        gap_label=gap_label,
        novel_terms=", ".join(novel_terms[:12]) or "(none — your terms all appear in close work)",
        works=_format_works(related_work),
    )
    raw = llm.complete(system=_IDEATE_SYSTEM, messages=[Message(role="user", content=prompt)], max_tokens=1200)  # type: ignore[attr-defined]
    return raw.strip()


__all__ = ["ideate", "write_review"]
