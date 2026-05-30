"""Workflow layer — the user picks a *goal*, the components run underneath.

The product promise is "tell me what you're doing, get everything relevant in one pass."
The user never has to know that a grant check is really verify + scan + gap; they pick the
goal and the layer composes the right components, sharing work (one scan feeds both the
gap analysis and the retrieved-prior-art the ideator/reviewer reads).

    grant  → verify + scan + gap     "is my proposal grounded, novel, and aware of prior art?"
    paper  → verify + scan           "are my citations real, and what will reviewers compare me to?"
    review → verify + scan + write   "audit their citations, surface missing prior art, draft a review"
    ideate → scan + gap + ideate     "what's the white space, and what should I try next?"

verify / scan / gap are deterministic and keyless. The generative steps (review's write,
ideate's ideate) require --llm and are grounded only in the evidence the others produced.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from deltasci.audit.base import AuditReport
from deltasci.audit.cache import AuditCache
from deltasci.compose import ideate as _ideate
from deltasci.compose import write_review
from deltasci.gap import GapReport, analyze_gap
from deltasci.scan import ScanReport, scan

# goal -> (human label, ordered component steps)
WORKFLOWS: dict[str, tuple[str, list[str]]] = {
    "grant": ("Writing a grant proposal", ["verify", "scan", "gap"]),
    "paper": ("Submitting a paper", ["verify", "scan"]),
    "review": ("Peer-reviewing a paper", ["verify", "scan", "review"]),
    "ideate": ("Ideating new directions", ["scan", "gap", "ideate"]),
}


@dataclass
class WorkflowReport:
    goal: str
    goal_label: str
    steps: list[str]
    verify: object | None = None  # AuditReport (snippet) | PaperReport (paper)
    scan: ScanReport | None = None
    gap: GapReport | None = None
    generated: dict[str, str] = field(default_factory=dict)  # "review" / "ideate" → text
    notes: list[str] = field(default_factory=list)

    def headline(self) -> str:
        bits: list[str] = []
        if self.verify is not None:
            bits.append(_audit_summary(self.verify))
        if self.gap is not None:
            bits.append(f"prior art: {self.gap.classification}")
        elif self.scan is not None:
            bits.append(f"{len(self.scan.hits)} related works")
        return " · ".join(bits) or "(nothing to report)"


def _audit_summary(report: object) -> str:
    if isinstance(report, AuditReport):
        return report.banner()
    counts = report.counts()  # type: ignore[attr-defined]
    return "Audit: " + (" · ".join(f"{k} {v}" for k, v in counts.items()) or "no citations")


def _audit_issues(report: object) -> list[str]:
    """The concrete citation problems a reviewer/author must act on, from either report shape."""

    issues: list[str] = []
    if isinstance(report, AuditReport):
        for f in report.findings:
            if f.status == "mismatch":
                why = "; ".join(f.mismatch_reasons) or "failed audit"
                issues.append(f"FAILED: {f.target_summary} — {why}")
            elif f.status in ("unverifiable", "skipped"):
                issues.append(f"{f.status.upper()}: {f.target_summary}")
        return issues
    for r in report.results:  # type: ignore[attr-defined]
        if r.verdict in ("FABRICATED", "METADATA-MISMATCH", "UNSUPPORTED"):
            marker = f"[{r.number}] " if r.number else ""
            issues.append(f"{r.verdict}: {marker}{r.reference_raw[:120]} (cited for: {r.claim[:80]})")
    return issues


def run_workflow(
    goal: str,
    text: str,
    *,
    llm: object | None = None,
    is_paper: bool = False,
    cache: AuditCache | None = None,
    limit: int = 10,
    sources: list[str] | None = None,
) -> WorkflowReport:
    """Run the components a `goal` needs, sharing the single scan across gap/review/ideate."""

    if goal not in WORKFLOWS:
        raise ValueError(f"unknown goal {goal!r}; choose from {', '.join(WORKFLOWS)}")
    label, steps = WORKFLOWS[goal]
    want = set(steps)
    run_verify = bool(want & {"verify", "review"})
    run_scan = bool(want & {"scan", "gap", "review", "ideate"})
    run_gap = bool(want & {"gap", "ideate"})

    rep = WorkflowReport(goal=goal, goal_label=label, steps=steps)

    if run_verify:
        if is_paper:
            from deltasci.paper import verify_paper

            rep.verify = verify_paper(text, cache=cache, llm=llm)
        else:
            from deltasci.verify import verify_text

            rep.verify = verify_text(text, cache=cache)

    if run_scan:
        rep.scan = scan(text, sources=sources, limit=limit)

    if run_gap:
        rep.gap = analyze_gap(text, scan_report=rep.scan, llm=llm)

    if "review" in want:
        if llm is None:
            rep.notes.append("review draft needs --llm (it is a generation step); ran verify + scan only.")
        else:
            rep.generated["review"] = write_review(
                text,
                _audit_summary(rep.verify) if rep.verify else "",
                _audit_issues(rep.verify) if rep.verify else [],
                rep.scan.hits if rep.scan else [],
                llm,
            )

    if "ideate" in want:
        if llm is None:
            rep.notes.append("ideation needs --llm (it is a generation step); ran scan + gap only.")
        else:
            rep.generated["ideate"] = _ideate(
                text,
                rep.gap.label if rep.gap else "",
                rep.gap.novel_terms if rep.gap else [],
                rep.scan.hits if rep.scan else [],
                llm,
            )

    return rep


# --- rendering ------------------------------------------------------------------------
def render_workflow_terminal(rep: WorkflowReport) -> str:
    from deltasci.gap import render_gap_terminal
    from deltasci.scan import render_scan_terminal

    out: list[str] = [
        f"━━ {rep.goal_label}  ({rep.goal}: {' + '.join(rep.steps)}) ━━",
        f"  {rep.headline()}",
        "",
    ]

    if rep.verify is not None:
        out.append("▶ CITATIONS")
        out.append(f"  {_audit_summary(rep.verify)}")
        for issue in _audit_issues(rep.verify)[:12]:
            out.append(f"    ✗ {issue}")
        out.append("")

    if rep.gap is not None:  # gap already prints the closest prior art
        out.append("▶ PRIOR ART + GAP")
        out.append(_indent(render_gap_terminal(rep.gap), "  "))
        out.append("")
    elif rep.scan is not None:
        out.append("▶ PRIOR ART")
        out.append(_indent(render_scan_terminal(rep.scan), "  "))
        out.append("")

    for name, title in (("review", "DRAFT REVIEW"), ("ideate", "NEW DIRECTIONS")):
        if name in rep.generated:
            out.append(f"▶ {title}")
            out.append(_indent(rep.generated[name], "  "))
            out.append("")

    for note in rep.notes:
        out.append(f"  ⓘ {note}")
    return "\n".join(out).rstrip() + "\n"


def _indent(text: str, prefix: str) -> str:
    return "\n".join(prefix + line for line in text.splitlines())


def workflow_payload(rep: WorkflowReport) -> dict:
    payload: dict = {
        "goal": rep.goal,
        "goal_label": rep.goal_label,
        "steps": rep.steps,
        "headline": rep.headline(),
        "generated": rep.generated,
        "notes": rep.notes,
    }
    if rep.verify is not None:
        if isinstance(rep.verify, AuditReport):
            from deltasci.verify import verify_payload

            payload["verify"] = verify_payload(rep.verify)
        else:
            from deltasci.paper import paper_payload

            payload["verify"] = paper_payload(rep.verify)  # type: ignore[arg-type]
    if rep.gap is not None:
        from deltasci.gap import gap_payload

        payload["gap"] = gap_payload(rep.gap)
    elif rep.scan is not None:
        from deltasci.scan import scan_payload

        payload["scan"] = scan_payload(rep.scan)
    return payload


__all__ = ["WORKFLOWS", "WorkflowReport", "render_workflow_terminal", "run_workflow", "workflow_payload"]
