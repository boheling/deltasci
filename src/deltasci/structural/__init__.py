"""Structural-biology helpers for DeltaScience.

Currently scopes to one job: derive a *reproducible* solvent-accessible (SA)
residue mask per HLA Class II locus from public PDB structures, as a
license-free proxy for HLA-EMMA's gated SA mask.

The output is named `dssp_sa_mismatch_count` everywhere it appears — NOT
`emma_sa_mm` — to make the comparability gap explicit. HLA-EMMA's official
list is hand-curated on top of this kind of computation; ours is reproducible
from public PDB IDs but is not equivalent.
"""

from deltasci.structural.dssp_sa import (
    SA_DATA_FILE,
    STRUCT_REFS,
    LocusSA,
    compute_all_loci,
    compute_sa_positions,
    load_sa_positions,
    write_sa_positions_json,
)

__all__ = [
    "SA_DATA_FILE",
    "STRUCT_REFS",
    "LocusSA",
    "compute_all_loci",
    "compute_sa_positions",
    "load_sa_positions",
    "write_sa_positions_json",
]
