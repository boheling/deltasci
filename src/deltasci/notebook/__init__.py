"""Notebook generator (v0.3.0).

Each domain pack may ship a `notebook.py` exporting a `build_cells(hypothesis,
plan)` function that returns a list of ipynb cells (using the helpers in
`deltasci.notebook.cells`). The generator wraps those cells into a complete
`.ipynb` JSON document plus a sibling `requirements.txt` and `README.md`.

Discipline
----------
- Generate-only. Notebooks are never auto-executed by deltasci.
- Pack-authored templates do the heavy lifting; the AI's contribution is
  filling in plan-derived parameters, not authoring novel code from scratch.
- Explicit TODO markers where substantive customization is the researcher's
  job. The header markdown cell + the README make it impossible to mistake
  the scaffold for finished work.
"""

from deltasci.notebook.cells import code_cell, markdown_cell
from deltasci.notebook.generator import (
    NotebookPack,
    generate_notebook_pack,
    pack_has_notebook_template,
)

__all__ = [
    "NotebookPack",
    "code_cell",
    "generate_notebook_pack",
    "markdown_cell",
    "pack_has_notebook_template",
]
