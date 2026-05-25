"""Tests for deterministic whole-paper parsing (offline, no network)."""

from __future__ import annotations

from deltasci.paper import (
    Reference,
    claim_for_reference,
    extract_identifier_references,
    find_in_text_cites,
    looks_numbered,
    parse_numbered_references,
    split_body_and_references,
)

_DOC = """Introduction

Tumor-associated macrophages drive osteosarcoma metastasis [1]. AlphaFold predicts
protein structure with near-experimental accuracy [2, 3]. Several methods have been
compared [2-4].

References

[1] Smith J, et al. Macrophages in osteosarcoma. Nature. 2020. doi:10.1038/s41586-020-1234-5
[2] Jumper J, et al. Highly accurate protein structure prediction with AlphaFold. Nature. 2021. PMID: 34265844
[3] Gu SQ, et al. Imaging findings in diagnosis. Asian J Surg. 2022.
[4] Doe A. Another method. J Methods. 2019.
"""


def test_split_body_and_references():
    body, refs = split_body_and_references(_DOC)
    assert "Tumor-associated macrophages" in body
    assert "Macrophages in osteosarcoma" in refs
    assert "Tumor-associated macrophages" not in refs


def test_parse_numbered_references():
    _, refs_text = split_body_and_references(_DOC)
    refs = parse_numbered_references(refs_text)
    assert [r.number for r in refs] == [1, 2, 3, 4]
    assert any(i.kind == "doi" and i.value == "10.1038/s41586-020-1234-5" for i in refs[0].identifiers)
    assert any(i.kind == "pmid" and i.value == "34265844" for i in refs[1].identifiers)
    assert refs[2].identifiers == []  # no embedded id → will need Crossref resolution


def test_find_in_text_cites_and_ranges():
    body, _ = split_body_and_references(_DOC)
    cites = find_in_text_cites(body)
    cited = {n for c in cites for n in c.numbers}
    assert cited == {1, 2, 3, 4}  # [1], [2,3], and [2-4] all expanded


def test_claim_for_reference_collects_context():
    body, _ = split_body_and_references(_DOC)
    cites = find_in_text_cites(body)
    claim2 = claim_for_reference(2, cites)
    assert "AlphaFold" in claim2  # the [2,3] sentence
    assert "compared" in claim2  # the [2-4] sentence also cites 2


def test_looks_numbered():
    body, refs_text = split_body_and_references(_DOC)
    refs = parse_numbered_references(refs_text)
    cites = find_in_text_cites(body)
    assert looks_numbered(refs, cites) is True
    assert looks_numbered([], cites) is False


def test_looks_numbered_rejects_appendix_numbering():
    # appendix rubric "numbers" repeat and don't start at 1 → not a real bibliography
    refs = [Reference(number=n, raw="x 2020") for n in (3, 3, 4, 3)]
    assert looks_numbered(refs, []) is False
    seq = [Reference(number=n, raw="x 2020") for n in (1, 2, 3, 4)]
    assert looks_numbered(seq, []) is True


def test_parse_filters_non_reference_numbered_items():
    # appendix list items without a year or identifier must not be parsed as references
    txt = (
        "1. Correctness — does the agent complete the task?\n"
        "2. Skill usage — does it invoke reusable skills?\n"
        "3. Smith J. A real paper. Nature, 2020. doi:10.1038/x12345\n"
    )
    refs = parse_numbered_references(txt)
    assert [r.number for r in refs] == [3]  # only the year/id-bearing entry survives


def test_extract_identifier_references_handles_arxiv_urls():
    txt = "Foo. Title. arXiv preprint arXiv:2303.08774, 2023. Bar. Other. URL https://arxiv.org/abs/2402.14740."
    refs = extract_identifier_references(txt)
    vals = {i.value for r in refs for i in r.identifiers}
    assert vals == {"2303.08774", "2402.14740"}


def test_year_range_not_treated_as_citation():
    cites = find_in_text_cites("Studies from [2018-2021] were reviewed.")
    # a 4-digit "range" of 3 spanning years must not expand into reference numbers
    assert cites == [] or all(not c.numbers for c in cites)
