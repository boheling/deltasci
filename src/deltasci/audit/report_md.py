"""Render audit findings for the standalone `deltasci verify` surface.

Maps each [`AuditFinding`][deltasci.audit.base.AuditFinding] to one of four
researcher-facing verdicts:

- ``PASS``               — identifier resolves, metadata matches (or the abstract supports the claim)
- ``FABRICATED``         — the cited identifier does not exist at all
- ``METADATA-MISMATCH``  — the identifier resolves but its record differs from the claim
- ``UNSUPPORTED``        — the paper is real but does not back the sentence it's cited for

Plus ``UNVERIFIABLE`` (no parseable identifier / too little to judge) and ``SKIPPED``
(network error). This is purpose-built for `verify`; the run-pipeline's
``_render_hypothesis_md`` keeps its own inline renderer for now — deduplicating the two
into one shared renderer is a worthwhile follow-up.
"""

from __future__ import annotations

from deltasci.audit.base import AuditFinding, AuditReport

# Verdict → (symbol, severity rank). Lower rank sorts first (most actionable on top).
_VERDICT_META = {
    "FABRICATED": ("✗", 0),
    "METADATA-MISMATCH": ("✗", 1),
    "UNSUPPORTED": ("⚠", 2),
    "UNVERIFIABLE": ("⊘", 3),
    "SKIPPED": ("…", 4),
    "PASS": ("✓", 5),
}


def verdict(finding: AuditFinding) -> str:
    """Collapse a finding's (status, target_kind, metadata) into one researcher verdict."""

    if finding.status == "verified":
        return "PASS"
    if finding.status == "skipped":
        return "SKIPPED"
    if finding.status == "unverifiable":
        return "UNVERIFIABLE"
    # status == "mismatch"
    if finding.target_kind in ("support", "quote"):
        return "UNSUPPORTED"
    if finding.fetched_metadata.get("found") is False:
        return "FABRICATED"
    return "METADATA-MISMATCH"


def _identifier_label(finding: AuditFinding) -> str:
    fm = finding.fetched_metadata
    return str(fm.get("pmid") or fm.get("doi") or fm.get("id") or fm.get("repo") or fm.get("accession") or "")


def summary_counts(report: AuditReport) -> dict[str, int]:
    counts: dict[str, int] = {}
    for f in report.findings:
        v = verdict(f)
        counts[v] = counts.get(v, 0) + 1
    return counts


def _sorted_findings(report: AuditReport) -> list[tuple[str, AuditFinding]]:
    pairs = [(verdict(f), f) for f in report.findings]
    pairs.sort(key=lambda p: _VERDICT_META[p[0]][1])
    return pairs


def render_findings_terminal(report: AuditReport, *, show_passed: bool = True) -> str:
    """Compact, one-line-per-finding terminal output."""

    if report.skipped:
        return report.banner()

    lines = [report.banner(), ""]
    counts = summary_counts(report)
    if counts:
        order = sorted(counts, key=lambda v: _VERDICT_META[v][1])
        lines.append("  ".join(f"{_VERDICT_META[v][0]} {v}: {counts[v]}" for v in order))
        lines.append("")

    for v, f in _sorted_findings(report):
        if v == "PASS" and not show_passed:
            continue
        sym = _VERDICT_META[v][0]
        ident = _identifier_label(f)
        ident_str = f" [{f.auditor_name}:{ident}]" if ident else f" [{f.auditor_name}]"
        lines.append(f"{sym} {v}{ident_str}")
        lines.append(f"    claim: {f.target_summary[:160]}")
        for r in f.mismatch_reasons[:2]:
            lines.append(f"    → {r}")
    return "\n".join(lines).rstrip() + "\n"


def render_findings_md(report: AuditReport) -> str:
    """Markdown report, grouped by verdict (actionable verdicts first)."""

    if report.skipped:
        return f"> {report.banner()}\n"

    lines = ["# Citation & claim verification", "", f"> {report.banner()}", ""]
    counts = summary_counts(report)
    if counts:
        order = sorted(counts, key=lambda v: _VERDICT_META[v][1])
        lines.append("| Verdict | Count |")
        lines.append("|---------|-------|")
        for v in order:
            lines.append(f"| {_VERDICT_META[v][0]} {v} | {counts[v]} |")
        lines.append("")

    grouped: dict[str, list[AuditFinding]] = {}
    for v, f in _sorted_findings(report):
        grouped.setdefault(v, []).append(f)

    for v in sorted(grouped, key=lambda x: _VERDICT_META[x][1]):
        lines.append(f"## {_VERDICT_META[v][0]} {v} ({len(grouped[v])})")
        lines.append("")
        for f in grouped[v]:
            ident = _identifier_label(f)
            head = f"**{f.auditor_name}**" + (f" · `{ident}`" if ident else "")
            lines.append(f"- {head}")
            lines.append(f"  - claim: {f.target_summary}")
            for r in f.mismatch_reasons:
                lines.append(f"  - reason: {r}")
            fm = f.fetched_metadata
            if v in ("METADATA-MISMATCH", "FABRICATED"):
                actual = ", ".join(
                    f"{k}={fm[k]!r}" for k in ("title", "year", "journal", "url") if fm.get(k)
                )
                if actual:
                    lines.append(f"  - actual record: {actual}")
            if v == "UNSUPPORTED" and fm.get("abstract_excerpt"):
                lines.append(f"  - abstract excerpt: {fm['abstract_excerpt'][:200]}…")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


__all__ = ["render_findings_md", "render_findings_terminal", "summary_counts", "verdict"]
