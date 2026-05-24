"""Unit tests for the structural / DSSP-SA module.

These tests exercise the pure-Python pieces (threshold logic, mature-numbering
offset, JSON round-trip, β1-domain filtering) on a synthetic structure that
fits in memory — so no PDB download is required during pytest. A separate
"live" smoke test (gated by `pytest -m live`) hits a real PDB if a contributor
wants to validate end-to-end.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from Bio.PDB.Atom import Atom
from Bio.PDB.Chain import Chain
from Bio.PDB.Model import Model
from Bio.PDB.Residue import Residue
from Bio.PDB.Structure import Structure

from deltasci.structural import (
    SA_DATA_FILE,
    STRUCT_REFS,
    LocusSA,
    compute_sa_positions,
    load_sa_positions,
    write_sa_positions_json,
)
from deltasci.structural.dssp_sa import (
    _MAX_ASA_TIEN_2013,
    _residue_sasa_iter,
    _select_chain,
)


# --- Synthetic structure helper ----------------------------------------------


_AAs = ["ALA", "VAL", "LEU", "ILE", "PHE", "TRP", "MET", "PRO", "GLY", "SER",
        "THR", "CYS", "TYR", "ASN", "GLN", "ASP", "GLU", "LYS", "ARG", "HIS"]


def _build_chain(chain_id: str, n_residues: int) -> Chain:
    """Build a Chain with `n_residues` standard amino-acid residues. Each
    residue gets a fake CA atom + a `.sasa` attribute that we control directly
    so we don't need to actually run ShrakeRupley in tests.
    """
    chain = Chain(chain_id)
    for i in range(1, n_residues + 1):
        resname = _AAs[(i - 1) % len(_AAs)]
        residue = Residue((" ", i, " "), resname, "")
        ca = Atom("CA", coord=(float(i), 0.0, 0.0), bfactor=0.0,
                  occupancy=1.0, altloc=" ", fullname=" CA ", serial_number=i,
                  element="C")
        residue.add(ca)
        # We'll set .sasa later in each test to control which residues are exposed.
        residue.sasa = 0.0
        chain.add(residue)
    return chain


def _build_structure(chain_id: str, n_residues: int) -> Structure:
    s = Structure("synthetic")
    m = Model(0)
    m.add(_build_chain(chain_id, n_residues))
    s.add(m)
    return s


# --- Tests --------------------------------------------------------------------


def test_struct_refs_cover_target_loci():
    """All loci the biomed-serology pack uses must have a default reference."""
    expected = {"DRB1", "DRB3", "DRB4", "DRB5", "DQA1", "DQB1", "DPA1", "DPB1"}
    assert expected.issubset(set(STRUCT_REFS.keys()))


def test_residue_iter_skips_non_standard_and_yields_relative_sasa():
    s = _build_structure("B", 5)
    chain = _select_chain(s, "B")
    # set sasa values: residue 3 is exposed, others buried
    for residue in chain:
        if residue.id[1] == 3:
            residue.sasa = _MAX_ASA_TIEN_2013["L"] * 0.5  # ~50% relative
        else:
            residue.sasa = 0.0

    out = list(_residue_sasa_iter(chain))
    # All 5 residues yielded with their relative SASA
    assert len(out) == 5
    res3 = [r for r in out if r[0] == 3][0]
    assert res3[2] == pytest.approx(0.5, rel=1e-3)
    res1 = [r for r in out if r[0] == 1][0]
    assert res1[2] == 0.0


def test_select_chain_returns_none_when_missing():
    s = _build_structure("B", 3)
    assert _select_chain(s, "Z") is None


def test_compute_sa_positions_thresholds_correctly_via_mock():
    """Patch ShrakeRupley + PDB download; verify thresholding + β1 cutoff."""
    s = _build_structure("B", 100)  # 100 residues; β1 cutoff = 94
    # Set sasa: residues 5, 10, 90 are above threshold; 95, 99 too — but
    # 95/99 are past β1 cutoff so they should be excluded.
    exposed = {5, 10, 90, 95, 99}
    for residue in s[0]["B"]:
        if residue.id[1] in exposed:
            residue.sasa = _MAX_ASA_TIEN_2013["A"] * 0.5  # rel ~0.5
        else:
            residue.sasa = _MAX_ASA_TIEN_2013["A"] * 0.05  # rel ~0.05 (buried)

    with patch("deltasci.structural.dssp_sa.PDBList") as mock_list, \
         patch("deltasci.structural.dssp_sa.PDBParser") as mock_parser, \
         patch("deltasci.structural.dssp_sa.ShrakeRupley") as mock_sr:
        mock_list.return_value.retrieve_pdb_file.return_value = "/tmp/_fake.pdb"
        mock_parser.return_value.get_structure.return_value = s
        mock_sr.return_value.compute = lambda structure, level: None  # we set .sasa manually

        positions, n_eval = compute_sa_positions(
            "FAKE", "B", threshold_rel_sasa=0.20,
            mature_first_res=1, beta1_end=94,
        )

    assert positions == [5, 10, 90], f"unexpected positions: {positions}"
    assert n_eval == 94  # all 1..94 evaluated; 95..100 excluded


def test_compute_sa_positions_respects_mature_offset():
    """If PDB numbering starts at residue 26 (signal-peptide retained), the
    `mature_first_res=26` offset should make output 1-based on mature."""
    chain = Chain("B")
    for pdb_num in range(26, 26 + 50):  # mature 1..50
        residue = Residue((" ", pdb_num, " "), "ALA", "")
        residue.add(Atom("CA", (0.0, 0.0, 0.0), 0.0, 1.0, " ", " CA ", pdb_num, "C"))
        # Mark residues 30 and 50 (PDB) = mature 5 and 25 as exposed
        residue.sasa = _MAX_ASA_TIEN_2013["A"] * 0.5 if pdb_num in (30, 50) else 0.0
        chain.add(residue)
    s = Structure("x"); m = Model(0); m.add(chain); s.add(m)

    with patch("deltasci.structural.dssp_sa.PDBList") as mock_list, \
         patch("deltasci.structural.dssp_sa.PDBParser") as mock_parser, \
         patch("deltasci.structural.dssp_sa.ShrakeRupley") as mock_sr:
        mock_list.return_value.retrieve_pdb_file.return_value = "/tmp/_fake.pdb"
        mock_parser.return_value.get_structure.return_value = s
        mock_sr.return_value.compute = lambda structure, level: None

        positions, _ = compute_sa_positions(
            "FAKE", "B", threshold_rel_sasa=0.20,
            mature_first_res=26, beta1_end=94,
        )
    assert positions == [5, 25]


def test_compute_sa_positions_raises_for_missing_chain():
    s = _build_structure("B", 5)
    with patch("deltasci.structural.dssp_sa.PDBList") as mock_list, \
         patch("deltasci.structural.dssp_sa.PDBParser") as mock_parser, \
         patch("deltasci.structural.dssp_sa.ShrakeRupley") as mock_sr:
        mock_list.return_value.retrieve_pdb_file.return_value = "/tmp/_fake.pdb"
        mock_parser.return_value.get_structure.return_value = s
        mock_sr.return_value.compute = lambda structure, level: None
        with pytest.raises(ValueError, match="chain 'Z' not found"):
            compute_sa_positions("FAKE", "Z")


def test_write_and_load_json_round_trip(tmp_path):
    loci = {
        "DRB1": LocusSA(
            locus="DRB1", reference_pdb="1AQD", chain_id="B",
            domain="beta1_mature_1_94", threshold_rel_sasa=0.20,
            positions=[1, 5, 9], n_residues_evaluated=91,
            notes="canonical DRB1",
        ),
    }
    metadata = {"computed_at": "2026-05-05T00:00:00Z", "threshold_rel_sasa": 0.20}
    out = tmp_path / "sa.json"
    write_sa_positions_json(loci, metadata, out_path=out)

    payload = load_sa_positions(out)
    assert "DRB1" in payload and payload["DRB1"]["positions"] == [1, 5, 9]
    assert payload["metadata"]["threshold_rel_sasa"] == 0.20


def test_committed_sa_positions_json_is_valid():
    """The committed file should load + cover the 8 expected loci with
    realistic position counts (between 5 and 60 per locus)."""
    if not SA_DATA_FILE.exists():
        pytest.skip("SA positions JSON not yet computed")
    payload = load_sa_positions()
    expected = {"DRB1", "DRB3", "DRB4", "DRB5", "DQA1", "DQB1", "DPA1", "DPB1"}
    assert expected.issubset(set(payload.keys()))
    for locus in expected:
        positions = payload[locus]["positions"]
        assert isinstance(positions, list) and 5 <= len(positions) <= 60, (
            f"{locus} has {len(positions)} positions — outside sanity bounds")
        assert all(isinstance(p, int) and 1 <= p <= 100 for p in positions)
    md = payload["metadata"]
    assert md["feature_name"] == "dssp_sa_mismatch_count"
    assert "not_equivalent_to" in md
    assert md["threshold_rel_sasa"] == pytest.approx(0.20)
