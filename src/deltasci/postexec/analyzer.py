"""Heuristic analyzer that matches notebook execution against the original report.

Inputs: a `summary.json` (risks, protocol, hypothesis) and the executed
`10_notebook/notebook.ipynb`. The notebook's `outputs` and the markdown
`Observation` cells inserted by the v0.6 cell-runner are the evidence trail.

Outputs (as a `PostExecReport`):
  - `metrics`        : measured Spearman ρ / lift / per-locus / etc.
  - `risk_statuses`  : per-risk classification + evidence quote
  - `next_step_statuses` : per protocol step, DONE/OUTSTANDING + evidence
  - `new_issues`     : placeholder/PLACEHOLDER:NOT-VERIFIED markers and
                       NotImplementedError gates that survived to final state
  - `achievements`   : narrative bullets the report should add (e.g. "MARCo
                       bulk extraction achieved via /api/correlation-matrix")
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Literal


# --- Public dataclasses -------------------------------------------------------


@dataclass
class ExecutionMetric:
    name: str             # canonical name, e.g. "pooled_spearman_rho"
    value: float
    pretty: str           # human-readable, e.g. "ρ = 0.8848"
    cell_index: int
    snippet: str = ""     # the line it came from, for traceability


@dataclass
class RiskStatus:
    risk_id: str
    severity: str
    description: str
    status: Literal["resolved", "still_open", "partly_resolved", "confirmed", "unknown"]
    evidence_cell: int | None = None
    evidence_snippet: str = ""
    rationale: str = ""


@dataclass
class NextStepStatus:
    order: int
    name: str
    status: Literal["done", "outstanding", "partial"]
    evidence_cell: int | None = None
    evidence_snippet: str = ""


@dataclass
class NewIssue:
    cell_index: int
    kind: Literal["placeholder", "researcher_gate", "synthetic_substitution", "warning"]
    message: str
    snippet: str = ""


@dataclass
class Achievement:
    headline: str
    detail: str = ""
    cell_index: int | None = None


@dataclass
class PostExecReport:
    metrics: list[ExecutionMetric] = field(default_factory=list)
    risk_statuses: list[RiskStatus] = field(default_factory=list)
    next_step_statuses: list[NextStepStatus] = field(default_factory=list)
    new_issues: list[NewIssue] = field(default_factory=list)
    achievements: list[Achievement] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "metrics": [m.__dict__ for m in self.metrics],
            "risk_statuses": [r.__dict__ for r in self.risk_statuses],
            "next_step_statuses": [s.__dict__ for s in self.next_step_statuses],
            "new_issues": [i.__dict__ for i in self.new_issues],
            "achievements": [a.__dict__ for a in self.achievements],
        }


# --- Metric extraction --------------------------------------------------------


_METRIC_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("pooled_spearman_rho",       re.compile(r"POOLED held-out Spearman\s*ρ:?\s*([\-+\d.]+)", re.I)),
    ("falsifiability_lift",       re.compile(r"lift over best baseline:?\s*([+\-]?[\d.]+)", re.I)),
    ("falsifiability_passed",     re.compile(r"falsifiability check\s+(PASSED|FAILED)", re.I)),
    ("best_baseline_rho",         re.compile(r"Best baseline:.*ρ\s*=\s*([\-+\d.]+)", re.I)),
    ("model_pooled_rho",          re.compile(r"pooled Spearman ρ \(model\):?\s*([\-+\d.]+)", re.I)),
    ("baseline_pooled_rho",       re.compile(r"pooled Spearman ρ \(baseline\):?\s*([\-+\d.]+)", re.I)),
    ("platform_discrepant_count", re.compile(r"Platform-discrepant pairs[^:]*:\s*([\d,]+)", re.I)),
    ("platform_consensus_rho",    re.compile(r"Predicted ρ vs cross-platform consensus[^=]*=\s*([\-+\d.]+)", re.I)),
    ("pairs_total",               re.compile(r"MARCo pairs:\s*([\d,]+)", re.I)),
    ("pairs_after_locus_filter",  re.compile(r"after locus filter:\s+([\d,]+)\s+pairs", re.I)),
]

_PER_LOCUS_RHO = re.compile(r"^\s*([A-Z][A-Z0-9]+)\s*:\s*n=\s*([\d,]+),?\s*ρ\s*=\s*([\-+\d.]+)", re.M)
# Starved per-locus rows say "n=6 (too small for stable ρ; skipped)"
_PER_LOCUS_STARVED = re.compile(r"^\s*([A-Z][A-Z0-9]+)\s*:\s*n=\s*([\d,]+)\s*\(too small", re.M)


def _to_float(s: str) -> float:
    return float(s.replace(",", ""))


def extract_metrics(cells: list[dict]) -> list[ExecutionMetric]:
    """Walk every code cell's stdout for known metric patterns."""
    metrics: list[ExecutionMetric] = []
    for i, c in enumerate(cells):
        if c.get("cell_type") != "code":
            continue
        text = ""
        for o in c.get("outputs", []) or []:
            if o.get("output_type") == "stream" and o.get("name") == "stdout":
                t = o.get("text", "")
                text += "".join(t) if isinstance(t, list) else t
        if not text:
            continue
        for name, pat in _METRIC_PATTERNS:
            m = pat.search(text)
            if m:
                raw = m.group(1)
                try:
                    val = _to_float(raw) if raw not in ("PASSED", "FAILED") else (1.0 if raw == "PASSED" else 0.0)
                except ValueError:
                    continue
                pretty = f"{name.replace('_', ' ')}: {raw}"
                snippet = m.group(0)
                metrics.append(ExecutionMetric(name=name, value=val, pretty=pretty, cell_index=i, snippet=snippet))
        # per-locus ρ (multiple matches per cell)
        for m in _PER_LOCUS_RHO.finditer(text):
            locus, n_str, rho_str = m.group(1), m.group(2), m.group(3)
            try:
                rho = _to_float(rho_str)
            except ValueError:
                continue
            metrics.append(ExecutionMetric(
                name=f"per_locus_rho_{locus}", value=rho,
                pretty=f"{locus} ρ = {rho:.4f} (n={n_str})",
                cell_index=i, snippet=m.group(0).strip(),
            ))
        # starved per-locus rows ("DRB3 : n=6 (too small for stable ρ; skipped)")
        for m in _PER_LOCUS_STARVED.finditer(text):
            locus, n_str = m.group(1), m.group(2)
            try:
                n = _to_float(n_str)
            except ValueError:
                continue
            metrics.append(ExecutionMetric(
                name=f"per_locus_starved_{locus}", value=n,
                pretty=f"{locus} starved (n={n_str})",
                cell_index=i, snippet=m.group(0).strip(),
            ))
    return metrics


# --- Risk / next-step matching ------------------------------------------------


# Token families per execution-success signal. Each family requires a
# *specific* compound token on the risk side — generic mentions of "HLAMatchmaker"
# or "DQ" are NOT enough to trigger a resolved status, because those words
# appear in many methodological risks that are NOT about pipeline feasibility.
_RESOLUTION_FAMILIES: list[tuple[str, list[str], list[str]]] = [
    # (label, risk-side trigger words, observation-side resolution words)
    (
        "bulk_extraction_via_api",
        # Must be about data-extraction feasibility specifically.
        ["bulk-extraction", "bulk extraction", "rate-limit", "rate limit",
         "extraction may take", "extraction feasibility", "scraper", "scraping",
         "no API exists"],
        ["/api/correlation-matrix", "via api", "/api/", "live api", "discover-api"],
    ),
    (
        "imgt_fasta_obtained",
        ["IPD-IMGT/HLA fasta", "hla_prot.fasta", "ANHIG", "anhig"],
        ["downloading", "downloaded:", "hla_prot.fasta", "2-field HLA alleles"],
    ),
    (
        "hats_pipeline_done",
        ["HATS Perl", "HATS subprocess", "HATS pipeline", "runDRB1", "perl HATS"],
        ["bridged HATS", "RESIDUES/", "TWORESULTS/", "bridged HATS for"],
    ),
    (
        "eplet_pipeline_done",
        # Must be about *access* (institutional / programmatic) — not generic
        # mentions of HLAMatchmaker or eplet that show up in methodological risks.
        ["HLAMatchmaker access", "PIRCHE-II access", "eplet batch", "eplet bulk",
         "programmatic batch", "institutional", "registry tables"],
        ["epregistry.com.br", "eplet features merged", "pair coverage  : ",
         "fetching https://www.epregistry"],
    ),
    (
        "heterodimer_handled",
        # Must talk about heterodimer *encoding/handling*, not just mention DQ.
        ["heterodimer encoding", "chain-aware", "DQ-heterodimer", "heterodimer chain",
         "heterodimer pair", "heterodimer notation"],
        ["heterodimer composites added", "heterodimer-aware", "split_heterodimer",
         "locus_DQ"],
    ),
]


# Risks whose `likely_failure_mode` describes specific observable outcomes
# (per-locus N, lift magnitude). For these, compare extracted metrics directly
# rather than rely on token families.
_NUMERIC_RISK_PATTERNS = [
    # (label, risk-side regex for thresholds, evaluator)
    # Lift threshold risks — "lift over best baseline" type
    ("lift_threshold",
     re.compile(r"lift.*?\+?([0-9]+\.[0-9]+)", re.I),
     "compare_lift"),
    # Sample-size-imbalance risks — "may have <1000 / DRB3/4/5 small N"
    ("sample_imbalance",
     re.compile(r"per[- ]locus.*?imbalance|small\s*N|underpowered|<\s*\d+\s*pairs?", re.I),
     "compare_locus_n"),
]


def _normalize(text: str) -> str:
    return text.lower()


def _hit_in(words: Iterable[str], text: str) -> bool:
    t = _normalize(text)
    return any(w.lower() in t for w in words)


def _gather_observation_text(cells: list[dict]) -> list[tuple[int, str]]:
    """Per-code-cell concatenated text (source + stdout + observation md after it)."""
    out: list[tuple[int, str]] = []
    for i, c in enumerate(cells):
        if c.get("cell_type") != "code":
            continue
        src = c.get("source") or []
        src_text = "".join(src) if isinstance(src, list) else (src or "")
        stdout_text = ""
        for o in c.get("outputs", []) or []:
            if o.get("output_type") == "stream" and o.get("name") == "stdout":
                t = o.get("text", "")
                stdout_text += "".join(t) if isinstance(t, list) else t
        # The Observation markdown cell for code cell `i` is the next markdown
        # cell whose deltasci.kind metadata == "observation" and of_cell == i.
        obs_text = ""
        for j in range(i + 1, min(i + 3, len(cells))):
            cj = cells[j]
            if cj.get("cell_type") != "markdown":
                continue
            meta = (cj.get("metadata") or {}).get("deltasci") or {}
            if meta.get("kind") == "observation":
                ot = cj.get("source") or []
                obs_text = "".join(ot) if isinstance(ot, list) else ot
                break
        out.append((i, src_text + "\n" + stdout_text + "\n" + obs_text))
    return out


def _classify_numeric_risk(
    risk_text: str,
    metrics: list[ExecutionMetric],
) -> tuple[Literal["resolved", "confirmed", "still_open"], str, int | None] | None:
    """For risks whose failure mode is numerically observable, compare measured
    metrics to the threshold mentioned in the risk text. Returns
    (status, rationale, evidence_cell) or None if not a numeric-style risk.
    """
    text_lower = risk_text.lower()

    # Lift-threshold risks: "+0.07 lift over best baseline is aggressive"
    is_lift_risk = (
        ("aggressive" in text_lower and "lift" in text_lower)
        or ("clinically marginal" in text_lower and "lift" in text_lower)
        or ("statistically detectable" in text_lower and "lift" in text_lower)
    )
    if is_lift_risk:
        # Pull the threshold expressed in the risk text
        m = re.search(r"\+([0-9]+\.[0-9]+)\s*(?:absolute\s+)?lift", risk_text)
        if not m:
            m = re.search(r"lift\s+(?:of\s+)?\+?([0-9]+\.[0-9]+)", risk_text, re.I)
        if not m:
            m = re.search(r"\+([0-9]+\.[0-9]+)", risk_text)
        risk_thr = float(m.group(1)) if m else None
        measured = next((mm for mm in metrics if mm.name == "falsifiability_lift"), None)
        if risk_thr is None or measured is None:
            return None
        if measured.value >= risk_thr:
            return ("resolved",
                    f"measured lift {measured.value:+.4f} ≥ stated threshold +{risk_thr:.4f}",
                    measured.cell_index)
        return ("confirmed",
                f"measured lift {measured.value:+.4f} < stated threshold +{risk_thr:.4f} — risk's failure mode held",
                measured.cell_index)

    # Sample-imbalance risks
    if re.search(r"per[\s\-]?locus.*imbalance|underpowered|small\s*N|few(?:er)?\s*pairs", text_lower):
        rho_loci = [m for m in metrics if m.name.startswith("per_locus_rho_")]
        starved_loci = [m for m in metrics if m.name.startswith("per_locus_starved_")]
        if not rho_loci and not starved_loci:
            return None
        if starved_loci:
            rep = ", ".join(f"{m.name.replace('per_locus_starved_', '')} n={int(m.value)}"
                            for m in starved_loci)
            return ("confirmed",
                    f"per-locus imbalance held: {len(starved_loci)} starved loci ({rep}); "
                    f"{len(rho_loci)} loci have n ≥ 20",
                    (starved_loci[0].cell_index
                     if starved_loci else rho_loci[0].cell_index))
        return ("resolved",
                f"all {len(rho_loci)} loci have n ≥ 20",
                rho_loci[0].cell_index)

    return None


def classify_risks(
    risks: list[dict],
    cells: list[dict],
    metrics: list[ExecutionMetric] | None = None,
) -> list[RiskStatus]:
    obs = _gather_observation_text(cells)
    metrics = metrics or extract_metrics(cells)
    statuses: list[RiskStatus] = []
    for r in risks or []:
        risk_text = " ".join([
            str(r.get("description", "")),
            str(r.get("likely_failure_mode", "")),
        ])
        # First try numeric-comparison risks; their answer is most informative.
        numeric = _classify_numeric_risk(risk_text, metrics)

        # Then token-family resolution
        best: tuple[str, int, str] | None = None
        for label, risk_words, resolution_words in _RESOLUTION_FAMILIES:
            if not _hit_in(risk_words, risk_text):
                continue
            for cell_idx, cell_text in obs:
                if _hit_in(resolution_words, cell_text):
                    line = ""
                    for ln in cell_text.splitlines():
                        if any(w.lower() in ln.lower() for w in resolution_words):
                            line = ln.strip()
                            break
                    best = (label, cell_idx, line)
                    break
            if best:
                break

        status: Literal["resolved", "still_open", "partly_resolved", "confirmed", "unknown"]
        evidence_cell, evidence_snippet, rationale = None, "", ""
        if numeric is not None:
            n_status, n_rationale, n_cell = numeric
            status = n_status
            rationale = n_rationale
            evidence_cell = n_cell
        elif best:
            status = "resolved"
            _label, evidence_cell, evidence_snippet = best
            rationale = f"matched resolution family `{_label}`"
        else:
            status = "still_open"
            rationale = "no observation cell matched the risk's resolution tokens"
        statuses.append(RiskStatus(
            risk_id=str(r.get("id", "?")),
            severity=str(r.get("severity", "")),
            description=str(r.get("description", ""))[:280],
            status=status,
            evidence_cell=evidence_cell,
            evidence_snippet=evidence_snippet,
            rationale=rationale,
        ))
    return statuses


def classify_next_steps(steps: list[dict], cells: list[dict]) -> list[NextStepStatus]:
    obs = _gather_observation_text(cells)
    statuses: list[NextStepStatus] = []
    for step in steps or []:
        name = str(step.get("name", ""))
        order = int(step.get("order", 0))
        # A step is DONE if an observation cell containing the step name reports
        # "executed cleanly" (✅) and not "failed" / "NotImplementedError".
        evidence_cell: int | None = None
        evidence_snippet = ""
        status: Literal["done", "outstanding", "partial"] = "outstanding"
        for cell_idx, cell_text in obs:
            t = cell_text.lower()
            if name.lower() in t and "executed cleanly" in t:
                status = "done"
                evidence_cell = cell_idx
                # Try to find a stdout headline for the snippet
                for ln in cell_text.splitlines():
                    if "ρ =" in ln or "spearman" in ln.lower() or "wrote" in ln.lower():
                        evidence_snippet = ln.strip()
                        break
                break
            if name.lower() in t and ("notimplementederror" in t or "failed" in t):
                status = "partial"
                evidence_cell = cell_idx
                break
        statuses.append(NextStepStatus(
            order=order, name=name, status=status,
            evidence_cell=evidence_cell, evidence_snippet=evidence_snippet,
        ))
    return statuses


def find_new_issues(cells: list[dict]) -> list[NewIssue]:
    issues: list[NewIssue] = []
    for i, c in enumerate(cells):
        if c.get("cell_type") != "code":
            continue
        src = c.get("source") or []
        src_text = "".join(src) if isinstance(src, list) else (src or "")
        if "PLACEHOLDER:NOT-VERIFIED" in src_text or "PLACEHOLDER:" in src_text:
            ln = next((l for l in src_text.splitlines() if "PLACEHOLDER" in l), "")
            issues.append(NewIssue(cell_index=i, kind="placeholder",
                                   message="cell still references a PLACEHOLDER:NOT-VERIFIED value",
                                   snippet=ln.strip()))
        if "SYNTHETIC" in src_text:
            ln = next((l for l in src_text.splitlines() if "SYNTHETIC" in l), "")
            issues.append(NewIssue(cell_index=i, kind="synthetic_substitution",
                                   message="cell uses a synthetic stand-in for a real source",
                                   snippet=ln.strip()))
        # Surviving NotImplementedError in cell outputs
        for o in c.get("outputs", []) or []:
            if o.get("output_type") == "error" and "NotImplementedError" in (o.get("ename") or ""):
                issues.append(NewIssue(cell_index=i, kind="researcher_gate",
                                       message="cell still raises NotImplementedError on execution",
                                       snippet=str(o.get("evalue", ""))[:160]))
    return issues


def derive_achievements(metrics: list[ExecutionMetric],
                        risk_statuses: list[RiskStatus]) -> list[Achievement]:
    """Headline bullets the regenerated report should lead with."""
    out: list[Achievement] = []
    pooled = next((m for m in metrics if m.name == "pooled_spearman_rho"), None)
    lift = next((m for m in metrics if m.name == "falsifiability_lift"), None)
    passed = next((m for m in metrics if m.name == "falsifiability_passed"), None)
    if pooled and lift and passed:
        verdict = "PASSED" if passed.value > 0 else "FAILED"
        out.append(Achievement(
            headline=f"Falsifiability gate {verdict} — pooled Spearman ρ = {pooled.value:.4f}, lift = {lift.value:+.4f}",
            detail=f"From cells {pooled.cell_index}/{lift.cell_index}; verdict from cell {passed.cell_index}.",
            cell_index=pooled.cell_index,
        ))
    per_locus = [m for m in metrics if m.name.startswith("per_locus_rho_")]
    if per_locus:
        loci = ", ".join(sorted(m.name.replace("per_locus_rho_", "") for m in per_locus))
        out.append(Achievement(
            headline=f"Per-locus stratification covers: {loci}",
            detail="; ".join(m.pretty for m in per_locus),
        ))
    for rs in risk_statuses:
        if rs.status == "resolved" and rs.severity in ("critical", "high"):
            out.append(Achievement(
                headline=f"Risk {rs.risk_id} ({rs.severity}) → resolved",
                detail=rs.evidence_snippet or rs.rationale,
                cell_index=rs.evidence_cell,
            ))
    return out


# --- Public entry point -------------------------------------------------------


def analyze_run(run_dir: Path | str) -> PostExecReport:
    run_dir = Path(run_dir)
    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    nb_path = run_dir / "10_notebook" / "notebook.ipynb"
    if not nb_path.is_file():
        raise FileNotFoundError(f"executed notebook not found at {nb_path}")
    nb = json.loads(nb_path.read_text(encoding="utf-8"))
    cells: list[dict] = nb.get("cells", []) or []

    risks = (summary.get("risks") or {}).get("items", []) or []
    steps = (summary.get("protocol") or {}).get("steps", []) or []

    metrics = extract_metrics(cells)
    risk_statuses = classify_risks(risks, cells, metrics=metrics)
    next_step_statuses = classify_next_steps(steps, cells)
    new_issues = find_new_issues(cells)
    achievements = derive_achievements(metrics, risk_statuses)

    return PostExecReport(
        metrics=metrics,
        risk_statuses=risk_statuses,
        next_step_statuses=next_step_statuses,
        new_issues=new_issues,
        achievements=achievements,
    )
