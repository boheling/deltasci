"""Tests for the gap analysis (offline; prior art is injected, not retrieved)."""

from __future__ import annotations

import deltasci.gap as gap_mod
from deltasci.gap import CONTESTED, CROWDED, INCONCLUSIVE, OPEN, analyze_gap, gap_payload
from deltasci.scan import ScanHit, ScanReport


def _hit(title: str, score: float, snippet: str = "", source: str = "openalex") -> ScanHit:
    return ScanHit(source, title, ["A. Author"], "2022", "Venue", f"https://x/{title[:5]}", "id", snippet, score)


def _report(terms: list[str], *hits: ScanHit, ok=("openalex", "arxiv", "pubmed"), failed=()) -> ScanReport:
    ranked = sorted(hits, key=lambda h: h.score, reverse=True)
    return ScanReport(query=" ".join(terms), terms=terms, hits=list(ranked), counts={},
                      ok_sources=list(ok), failed_sources=list(failed))


def test_crowded_when_top_is_strong_and_multiple_close():
    rep = _report(
        ["cathode", "voltage", "graph"],
        _hit("Graph nets for cathode voltage", 0.7),
        _hit("Cathode voltage via graph models", 0.5),
    )
    g = analyze_gap("graph cathode voltage", scan_report=rep)
    assert g.classification == CROWDED
    assert g.n_close == 2


def test_contested_when_one_adjacent_work():
    rep = _report(["cathode", "voltage"], _hit("Adjacent cathode study", 0.45))
    g = analyze_gap("cathode voltage", scan_report=rep)
    assert g.classification == CONTESTED


def test_open_when_no_strong_overlap():
    rep = _report(["cathode", "voltage"], _hit("Loosely related work", 0.2))
    g = analyze_gap("cathode voltage", scan_report=rep)
    assert g.classification == OPEN


def test_no_hits_is_open_and_thin_when_retrieval_healthy():
    rep = _report(["cathode", "voltage"])  # all scholarly corpora answered, just found nothing
    g = analyze_gap("cathode voltage", scan_report=rep)
    assert g.classification == OPEN
    assert g.thin is True
    assert g.top_overlap == 0.0


# --- the humility fix: absence claims require trustworthy retrieval ------------------
def test_open_downgrades_to_inconclusive_when_a_scholarly_source_failed():
    # No hits, but OpenAlex never answered — we cannot honestly call the space open.
    rep = _report(["cathode", "voltage"], ok=["arxiv", "pubmed"], failed=["openalex"])
    g = analyze_gap("cathode voltage", scan_report=rep)
    assert g.classification == INCONCLUSIVE
    assert "openalex" in g.failed_sources
    assert g.retrieval_ok is False


def test_low_overlap_also_downgrades_to_inconclusive_when_source_failed():
    rep = _report(["cathode", "voltage"], _hit("Loosely related", 0.2), ok=["pubmed"], failed=["openalex", "arxiv"])
    g = analyze_gap("cathode voltage", scan_report=rep)
    assert g.classification == INCONCLUSIVE  # would have been OPEN with full retrieval


def test_crowded_still_asserts_even_if_a_source_failed():
    # Presence is robust: a found 0.7 match can't be un-found by a rate-limited source.
    rep = _report(["cathode", "voltage"], _hit("Cathode voltage A", 0.7), _hit("Cathode voltage B", 0.5),
                  ok=["arxiv"], failed=["pubmed"])
    g = analyze_gap("cathode voltage", scan_report=rep)
    assert g.classification == CROWDED


def test_inconclusive_when_no_scholarly_corpus_was_queried():
    rep = _report(["cathode"], ok=["github"], failed=[])  # only github → can't claim literature is open
    g = analyze_gap("cathode", scan_report=rep)
    assert g.classification == INCONCLUSIVE


def test_distinguishing_terms_are_those_no_close_work_mentions():
    # "cathode" and "voltage" appear in a hit; "electrolyte" appears in none.
    rep = _report(
        ["electrolyte", "cathode", "voltage"],
        _hit("Cathode voltage prediction", 0.6, snippet="predicting cathode voltage"),
    )
    g = analyze_gap("electrolyte cathode voltage", scan_report=rep)
    assert "electrolyte" in g.novel_terms
    assert "cathode" in g.covered_terms and "voltage" in g.covered_terms
    assert "electrolyte" not in g.covered_terms


def test_analyze_runs_scan_when_no_report_given(monkeypatch):
    called = {}

    def fake_scan(text, **kw):
        called["text"] = text
        return _report(["graph", "voltage"], _hit("Graph voltage model", 0.5))

    monkeypatch.setattr(gap_mod, "scan", fake_scan)
    g = analyze_gap("graph voltage idea", limit=5)
    assert called["text"] == "graph voltage idea"
    assert g.classification in (CROWDED, CONTESTED, OPEN)


class _FakeLLM:
    def __init__(self, text="Prior work covers X (Author 2022). Distinguishing angle: Y"):
        self.text = text
        self.seen = None

    def complete(self, system, messages, max_tokens=2048):
        self.seen = messages[0].content
        return self.text


def test_llm_narrative_is_grounded_and_attached():
    rep = _report(["cathode", "voltage"], _hit("Cathode voltage paper", 0.6, snippet="voltage prediction"))
    llm = _FakeLLM()
    g = analyze_gap("cathode voltage idea", scan_report=rep, llm=llm)
    assert g.narrative and "Distinguishing angle" in g.narrative
    assert "Cathode voltage paper" in llm.seen  # the real retrieved work was fed to the model


def test_llm_failure_does_not_sink_report():
    class Boom:
        def complete(self, *a, **k):
            raise RuntimeError("provider down")

    rep = _report(["cathode"], _hit("Cathode paper", 0.6))
    g = analyze_gap("cathode", scan_report=rep, llm=Boom())
    assert g.narrative is None  # narrative is optional commentary
    assert g.classification == CONTESTED  # deterministic verdict still produced (one strong work)


def test_no_llm_call_when_no_hits():
    rep = _report(["cathode"])  # empty hits
    g = analyze_gap("cathode", scan_report=rep, llm=_FakeLLM())
    assert g.narrative is None


def test_gap_payload_shape():
    rep = _report(
        ["cathode", "voltage"],
        _hit("Cathode voltage paper", 0.6),
        _hit("Voltage from cathode graphs", 0.5),
    )
    g = analyze_gap("cathode voltage", scan_report=rep)
    p = gap_payload(g)
    assert p["classification"] == CROWDED
    assert set(["query", "terms", "top_overlap", "novel_terms", "scan"]).issubset(p)
    assert "hits" in p["scan"]
