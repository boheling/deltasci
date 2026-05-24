"""Post-execution feedback loop for DeltaScience runs.

Walks an executed notebook + summary.json and produces a structured update:
  - measured metrics extracted from observation cells (Spearman ρ, lift, etc.)
  - risk-status table (RESOLVED / STILL_OPEN / NEW) with evidence quotes
  - next-step status (DONE / OUTSTANDING)
  - new issues surfaced by the execution log

Default mode is heuristic / rule-based — token overlap between risk text and
notebook observations + regex extraction of common metric patterns. An LLM-aided
rewrite is deferred to v0.8.1; the heuristic surface is deterministic and
auditable, which is the right starting point for the audit pillar.
"""

from deltasci.postexec.analyzer import (
    Achievement,
    ExecutionMetric,
    NewIssue,
    NextStepStatus,
    PostExecReport,
    RiskStatus,
    analyze_run,
)
from deltasci.postexec.renderer import (
    render_addendum_markdown,
    render_risks_markdown_with_status,
    update_summary_json,
)

__all__ = [
    "Achievement",
    "ExecutionMetric",
    "NewIssue",
    "NextStepStatus",
    "PostExecReport",
    "RiskStatus",
    "analyze_run",
    "render_addendum_markdown",
    "render_risks_markdown_with_status",
    "update_summary_json",
]
