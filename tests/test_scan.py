"""Tests for the prior-art scan (offline; mocked source queries)."""

from __future__ import annotations

import deltasci.scan as scan_mod
from deltasci.scan import ScanHit, _openalex_abstract, _query_openalex, query_terms, scan


def test_openalex_abstract_reconstruction():
    inv = {"Graph": [0], "neural": [1], "networks": [2], "predict": [3], "voltage": [4]}
    assert _openalex_abstract(inv) == "Graph neural networks predict voltage"
    assert _openalex_abstract(None) == ""


def test_query_terms_prefers_specific_terms():
    terms = query_terms("graph neural networks predict Li-ion cathode voltage")
    assert "cathode" in terms and "voltage" in terms and "neural" in terms
    assert "the" not in terms


def test_query_terms_strips_identifier_noise_but_keeps_markers():
    terms = query_terms("CD8 IL-6 macrophage PMID 35562209 arxiv 2101.00001 voltage in 2023")
    assert "35562209" not in terms and "2101" not in terms and "2023" not in terms
    assert "pmid" not in terms and "arxiv" not in terms  # citation scaffolding is not a topic
    assert "cd8" in terms or "il-6" in terms  # real markers survive


def test_query_terms_ignores_all_caps_title_stopwords():
    # Regression: an ALL-CAPS title word like "FOR" satisfies the acronym heuristic
    # (2+ uppercase letters) but is a stopword, not a topic. It must never reach the query.
    terms = query_terms("REINFORCEMENT LEARNING FOR SKILL EVOLUTION WITH agents and reasoning")
    assert "for" not in terms and "with" not in terms and "and" not in terms


def test_query_terms_ranks_by_frequency_not_length():
    # Regression: ranking by length surfaced one-off neologisms over recurring topic words.
    # A frequently-repeated topic word must outrank a long word that appears once.
    text = "reasoning reasoning reasoning reasoning skill skill skill superlongneologismword"
    terms = query_terms(text, k=2)
    assert "reasoning" in terms  # most frequent wins a slot
    assert "superlongneologismword" not in terms  # a single long token does not


def test_scan_uses_explicit_queries_when_given(monkeypatch):
    # The agent-driven primitive: explicit queries override term extraction, and each is
    # searched verbatim. (Scoring terms are derived from the queries when no idea text.)
    issued = []
    monkeypatch.setitem(scan_mod._SOURCES, "openalex", lambda q, n, t: issued.append(q) or [])
    qs = ["llm agent skill learning", "reinforcement learning credit assignment"]
    report = scan(queries=qs, sources=["openalex"])
    assert sorted(issued) == sorted(qs)  # both searched verbatim (order is concurrent)
    assert report.queries == qs  # preserved in report order
    assert report.query == qs[0]


def test_scan_query_is_capped_to_query_term_limit(monkeypatch):
    # The string actually sent to sources uses only the top QUERY_TERM_LIMIT terms, so a
    # paper's own coined name cannot over-constrain an AND query down to zero recall.
    monkeypatch.setitem(scan_mod._SOURCES, "openalex", lambda q, n, t: [])
    report = scan(
        "alpha alpha alpha beta beta beta gamma gamma delta epsilon zeta skillevoname",
        sources=["openalex"],
    )
    assert len(report.query.split()) <= scan_mod.QUERY_TERM_LIMIT


def test_query_openalex_parses_results(monkeypatch):
    monkeypatch.setattr(
        scan_mod,
        "get_json",
        lambda *a, **k: {
            "results": [
                {
                    "title": "Graph networks for cathode voltage",
                    "publication_year": 2022,
                    "authorships": [{"author": {"display_name": "A. Researcher"}}],
                    "primary_location": {"source": {"display_name": "Nature Materials"}},
                    "doi": "https://doi.org/10.1/x",
                    "abstract_inverted_index": {"cathode": [0], "voltage": [1]},
                }
            ]
        },
    )
    hits = _query_openalex("cathode voltage", 5, 10.0)
    assert len(hits) == 1
    assert hits[0].source == "openalex"
    assert hits[0].year == "2022"
    assert "cathode voltage" in hits[0].snippet


def test_scan_dedups_and_ranks(monkeypatch):
    relevant = ScanHit("openalex", "Graph neural networks for cathode voltage", ["X"], "2022", "Nat Mater",
                       "https://doi.org/10.1/a", "10.1/a", "Predicting cathode voltage with GNNs.")
    dup = ScanHit("arxiv", "Graph neural networks for cathode voltage", ["Y"], "2021", "arXiv",
                  "https://arxiv.org/abs/2101.00001", "2101.00001", "")
    unrelated = ScanHit("arxiv", "Migratory patterns of arctic birds", ["Z"], "2020", "arXiv",
                        "https://arxiv.org/abs/2002.00002", "2002.00002", "Bird migration study.")
    monkeypatch.setitem(scan_mod._SOURCES, "openalex", lambda q, n, t: [relevant])
    monkeypatch.setitem(scan_mod._SOURCES, "arxiv", lambda q, n, t: [dup, unrelated])

    report = scan("graph neural networks predict cathode voltage", sources=["openalex", "arxiv"])
    titles = [h.title for h in report.hits]
    assert len(report.hits) == 2  # the duplicate title is collapsed
    assert "Graph neural networks for cathode voltage" in titles[0]  # most relevant ranks first
    assert report.hits[0].score > report.hits[1].score


def test_scan_empty_query_returns_empty():
    assert scan("the and of a").hits == []  # only stopwords → nothing to search


def test_failing_source_does_not_sink_scan(monkeypatch):
    def boom(q, n, t):
        raise RuntimeError("network down")

    good = ScanHit("openalex", "Cathode voltage prediction via graph networks", [], "2023", "", "u", "i", "")
    monkeypatch.setitem(scan_mod._SOURCES, "openalex", lambda q, n, t: [good])
    monkeypatch.setitem(scan_mod._SOURCES, "arxiv", boom)
    report = scan("graph cathode voltage prediction", sources=["openalex", "arxiv"])
    assert len(report.hits) == 1  # arxiv blew up; openalex result still returned
    assert report.ok_sources == ["openalex"]  # responded
    assert report.failed_sources == ["arxiv"]  # recorded as a coverage gap, not silently dropped


def test_empty_result_counts_as_ok_not_failed(monkeypatch):
    # A source that responds with zero results is healthy — distinct from one that errors.
    monkeypatch.setitem(scan_mod._SOURCES, "openalex", lambda q, n, t: [])
    monkeypatch.setitem(scan_mod._SOURCES, "pubmed", lambda q, n, t: (_ for _ in ()).throw(RuntimeError("429")))
    report = scan("graph cathode voltage", sources=["openalex", "pubmed"])
    assert report.ok_sources == ["openalex"]
    assert report.failed_sources == ["pubmed"]
