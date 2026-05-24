"""Compute solvent-accessible residue masks per HLA Class II locus from public
PDB structures. Pure-Python via Biopython's ShrakeRupley implementation — no
external `mkdssp` binary required.

This is a *DSSP-style* SA proxy, not the HLA-EMMA mask. The output column is
`dssp_sa_mismatch_count` everywhere downstream, and the metadata block names
the reference PDB + chain + threshold + β1-domain residue range so a reviewer
can replicate the mask from first principles.

Default behavior:
  - Threshold:  relative SASA ≥ 0.20  (Tien et al. 2013 Max-ASA convention)
  - Domain:     β1 mature-protein residues 1–94 only (the antibody-recognized,
                polymorphic peptide-binding-groove face for Class II)
  - Reference:  one high-resolution PDB per locus (single-PDB strategy;
                consensus-over-N-structures is a future opt-in)
  - Probe:      1.4 Å (water) · n_points = 100 for the surface mesh
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from Bio.PDB import PDBList, PDBParser
from Bio.PDB.Chain import Chain
from Bio.PDB.SASA import ShrakeRupley
from Bio.PDB.Structure import Structure


# --- Reference PDB choices ----------------------------------------------------
# `pdb_id` is the RCSB code; `chain_id` is the chain in the asymmetric unit
# carrying the locus's β chain (or α chain, for DQA1/DPA1). `mature_first_res`
# is the residue number in the deposited PDB that corresponds to position 1 of
# the *mature* protein — used to translate PDB numbering to mature numbering.

@dataclass
class StructRef:
    pdb_id: str
    chain_id: str
    mature_first_res: int  # PDB residue number that maps to mature position 1
    beta1_end: int = 94    # last mature position included in β1 domain
    notes: str = ""


# Default reference set. These are the structures we run by default; if the
# user supplies their own, we pass through. PDB IDs verified against rcsb.org.
STRUCT_REFS: dict[str, StructRef] = {
    "DRB1": StructRef("1AQD", "B", mature_first_res=1, notes="DR1 + HA306-318; canonical DRB1 reference, 2.45 Å"),
    "DRB3": StructRef("3C5J", "B", mature_first_res=1, notes="DR52 / DRB3*03:01, 2.40 Å"),
    "DRB4": StructRef("6CQR", "B", mature_first_res=1, notes="DR53 / DRB4*01:03, 1.90 Å"),
    "DRB5": StructRef("1H15", "B", mature_first_res=1, notes="DR2 / DRB5*01:01, 2.60 Å"),
    "DQA1": StructRef("1JK8", "A", mature_first_res=1, notes="DQ8 α chain (DQA1*03:01), 2.40 Å"),
    "DQB1": StructRef("1JK8", "B", mature_first_res=1, notes="DQ8 β chain (DQB1*03:02), 2.40 Å"),
    "DPA1": StructRef("3LQZ", "A", mature_first_res=1, notes="DP2 α chain (DPA1*02:01), 1.65 Å"),
    "DPB1": StructRef("3LQZ", "B", mature_first_res=1, notes="DP2 β chain (DPB1*02:01), 1.65 Å"),
}


# --- Tien et al. 2013 empirical max-ASA reference (Å²) ------------------------
# Used to normalize per-residue SASA into relative SASA. Source: PLoS ONE 2013
# Vol 8 e80635 — empirical maxima from 11,000+ Gly-X-Gly fragments. Hard-coded
# here so the module has zero data dependencies.

_MAX_ASA_TIEN_2013: dict[str, float] = {
    "A": 129.0, "C": 167.0, "D": 193.0, "E": 223.0, "F": 240.0,
    "G":  85.0, "H": 224.0, "I": 197.0, "K": 236.0, "L": 201.0,
    "M": 224.0, "N": 195.0, "P": 159.0, "Q": 225.0, "R": 274.0,
    "S": 155.0, "T": 172.0, "V": 174.0, "W": 285.0, "Y": 263.0,
}


# Three-letter → one-letter for amino acids (Biopython residue names).
_THREE_TO_ONE: dict[str, str] = {
    "ALA": "A", "ARG": "R", "ASN": "N", "ASP": "D", "CYS": "C",
    "GLU": "E", "GLN": "Q", "GLY": "G", "HIS": "H", "ILE": "I",
    "LEU": "L", "LYS": "K", "MET": "M", "PHE": "F", "PRO": "P",
    "SER": "S", "THR": "T", "TRP": "W", "TYR": "Y", "VAL": "V",
}


# --- Output data shape --------------------------------------------------------


@dataclass
class LocusSA:
    locus: str
    reference_pdb: str
    chain_id: str
    domain: str                    # e.g., "beta1_mature_1_94"
    threshold_rel_sasa: float
    positions: list[int] = field(default_factory=list)
    n_residues_evaluated: int = 0
    notes: str = ""

    def to_dict(self) -> dict:
        return self.__dict__


SA_DATA_FILE = Path(__file__).parent / "data" / "sa_positions_v1.json"


# --- Computation --------------------------------------------------------------


def _select_chain(structure: Structure, chain_id: str) -> Chain | None:
    """Return the requested chain from the first model; None if not present."""
    for model in structure:
        for chain in model:
            if chain.id == chain_id:
                return chain
    return None


def _residue_sasa_iter(chain: Chain) -> Iterable[tuple[int, str, float]]:
    """Yield (mature_position, residue_letter, relative_SASA) for amino-acid
    residues only. Skips heteroatoms / waters / non-standard residues.

    Numbering: uses the residue's `id[1]` (PDB residue number) directly. The
    caller subtracts the mature-first-res offset.
    """
    for residue in chain:
        het, res_num, _icode = residue.id
        if het.strip():  # heteroatom / water
            continue
        resname = residue.resname.strip().upper()
        one = _THREE_TO_ONE.get(resname)
        if one is None:
            continue
        max_asa = _MAX_ASA_TIEN_2013.get(one)
        if max_asa is None or max_asa <= 0:
            continue
        try:
            sasa_abs = float(residue.sasa)  # set by ShrakeRupley.compute(level="R")
        except AttributeError:
            continue
        rel = sasa_abs / max_asa
        yield res_num, one, rel


def compute_sa_positions(
    pdb_id: str,
    chain_id: str,
    *,
    threshold_rel_sasa: float = 0.20,
    mature_first_res: int = 1,
    beta1_end: int = 94,
    pdb_cache_dir: Path | None = None,
    probe_radius: float = 1.4,
    n_points: int = 100,
) -> tuple[list[int], int]:
    """Return (positions, n_residues_evaluated).

    `positions` are 1-indexed mature-protein residue numbers whose relative
    SASA on the chosen chain ≥ `threshold_rel_sasa`, restricted to the β1
    domain (mature residues 1..`beta1_end`).
    """
    pdb_cache_dir = Path(pdb_cache_dir) if pdb_cache_dir else (Path(__file__).parent / "_pdb_cache")
    pdb_cache_dir.mkdir(parents=True, exist_ok=True)
    pdbl = PDBList(verbose=False, server="https://files.wwpdb.org")
    fpath = pdbl.retrieve_pdb_file(pdb_id, pdir=str(pdb_cache_dir), file_format="pdb")
    structure = PDBParser(QUIET=True).get_structure(pdb_id, fpath)
    chain = _select_chain(structure, chain_id)
    if chain is None:
        raise ValueError(f"chain {chain_id!r} not found in {pdb_id} (have: "
                         f"{sorted({c.id for m in structure for c in m})})")

    # Compute SASA in place — adds .sasa to each residue at level='R'.
    sr = ShrakeRupley(probe_radius=probe_radius, n_points=n_points)
    sr.compute(structure, level="R")

    positions: list[int] = []
    n_eval = 0
    for res_num, _aa, rel in _residue_sasa_iter(chain):
        mature_pos = res_num - mature_first_res + 1
        if mature_pos < 1 or mature_pos > beta1_end:
            continue
        n_eval += 1
        if rel >= threshold_rel_sasa:
            positions.append(mature_pos)
    return sorted(set(positions)), n_eval


def compute_all_loci(
    *,
    threshold_rel_sasa: float = 0.20,
    pdb_cache_dir: Path | None = None,
    refs: dict[str, StructRef] | None = None,
) -> tuple[dict[str, LocusSA], dict]:
    """Compute SA positions for every locus in `refs` (default: STRUCT_REFS)."""
    refs = refs if refs is not None else STRUCT_REFS
    loci: dict[str, LocusSA] = {}
    for locus, ref in refs.items():
        positions, n_eval = compute_sa_positions(
            ref.pdb_id, ref.chain_id,
            threshold_rel_sasa=threshold_rel_sasa,
            mature_first_res=ref.mature_first_res,
            beta1_end=ref.beta1_end,
            pdb_cache_dir=pdb_cache_dir,
        )
        loci[locus] = LocusSA(
            locus=locus,
            reference_pdb=ref.pdb_id,
            chain_id=ref.chain_id,
            domain=f"beta1_mature_1_{ref.beta1_end}",
            threshold_rel_sasa=threshold_rel_sasa,
            positions=positions,
            n_residues_evaluated=n_eval,
            notes=ref.notes,
        )
    metadata = {
        "method": "Bio.PDB.SASA.ShrakeRupley (Shrake-Rupley algorithm; pure Python)",
        "max_asa_reference": "Tien et al. 2013, PLoS ONE 8:e80635 (Gly-X-Gly empirical maxima)",
        "feature_name": "dssp_sa_mismatch_count",
        "not_equivalent_to": "HLA-EMMA official SA mask (license-gated; this is a public DSSP-style proxy)",
        "computed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "threshold_rel_sasa": threshold_rel_sasa,
        "domain": "beta1_mature_1_94",
        "single_pdb_strategy": True,
    }
    return loci, metadata


def write_sa_positions_json(
    loci: dict[str, LocusSA],
    metadata: dict,
    out_path: Path | None = None,
) -> Path:
    out_path = Path(out_path) if out_path else SA_DATA_FILE
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        **{l.locus: l.to_dict() for l in loci.values()},
        "metadata": metadata,
    }
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return out_path


def load_sa_positions(path: Path | None = None) -> dict:
    """Load the committed JSON. Returns the full payload, including metadata.

    Downstream callers typically want `{locus: positions}`; build it via
    `{k: v["positions"] for k, v in load_sa_positions().items() if k != "metadata"}`.
    """
    path = Path(path) if path else SA_DATA_FILE
    return json.loads(path.read_text(encoding="utf-8"))
