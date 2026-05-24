"""Preflight: static analysis of a notebook scaffold before execution.

Catches the failure classes the v0.5 case study identified:
- NameError-prone cross-cell variable references (test step uses `y` but no
  prior cell defines it)
- File paths referenced but not present
- `raise NotImplementedError` calls (researcher gates) — surfaced with the
  exact message the user will see
- TODO and PLACEHOLDER markers — counted separately because they have
  different stakes (TODO = "fill in", PLACEHOLDER = "synthetic value
  pretending to be real, replace before relying")
"""

from deltasci.preflight.analyzer import PreflightReport, analyze_notebook

__all__ = ["PreflightReport", "analyze_notebook"]
