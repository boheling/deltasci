from __future__ import annotations

from deltasci.audit.extractor import extract_identifiers


def test_pmid_extracts():
    ids = extract_identifiers("Smith et al 2022, Nature, PMID 35562209")
    assert any(i.kind == "pmid" and i.value == "35562209" for i in ids)


def test_pmid_with_colon():
    ids = extract_identifiers('source="Liu 2022, PMID:35189789"')
    assert any(i.kind == "pmid" and i.value == "35189789" for i in ids)


def test_doi_extracts():
    ids = extract_identifiers("Loupy 2019, doi:10.1016/S0140-6736(19)30568-0")
    assert any(i.kind == "doi" and i.value.startswith("10.1016") for i in ids)


def test_doi_strips_trailing_punct():
    ids = extract_identifiers("see 10.1038/nature01234.")
    dois = [i.value for i in ids if i.kind == "doi"]
    assert "10.1038/nature01234" in dois


def test_arxiv_modern_format():
    ids = extract_identifiers("see arXiv:2206.11888v2 for the HGT paper")
    assert any(i.kind == "arxiv" and i.value.startswith("2206.11888") for i in ids)


def test_github_repo_extracts():
    ids = extract_identifiers("github.com/pyg-team/pytorch_geometric is the canonical impl")
    assert any(i.kind == "github" and i.value == "pyg-team/pytorch_geometric" for i in ids)


def test_huggingface_extracts():
    ids = extract_identifiers("see huggingface.co/microsoft/biogpt for the model")
    assert any(i.kind == "huggingface" and i.value == "microsoft/biogpt" for i in ids)


def test_geo_accession_extracts():
    ids = extract_identifiers("Liu et al 2022, GEO accession GSE152048")
    assert any(i.kind == "geo" and i.value == "GSE152048" for i in ids)


def test_no_identifier_returns_empty():
    ids = extract_identifiers("Susal & Opelz, Collaborative Transplant Study, multiple papers e.g. Clin Transpl 2007")
    assert all(i.kind not in ("pmid", "doi", "arxiv", "github", "geo") for i in ids)


def test_multiple_identifiers_in_one_string():
    ids = extract_identifiers("Liu 2022, PMID 35189789, doi:10.1016/j.celrep.2022.110600, GEO GSE152048")
    kinds = {i.kind for i in ids}
    assert "pmid" in kinds
    assert "doi" in kinds
    assert "geo" in kinds
