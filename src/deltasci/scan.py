"""Prior-art scan — the grounded "has this been done?" component.

Given a research idea or a paper, retrieve the closest *real* works from public corpora
(OpenAlex, arXiv, PubMed, GitHub) and rank them by similarity to the input. Every result
is a real, clickable record — the scan answers "what already exists near this" with
evidence, not an LLM's opinion. This is the keystone the grant / paper / review / ideate
workflows compose, alongside `verify`.

Deterministic: real API search + salient-term overlap ranking. No LLM, no API key.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Callable

from deltasci.audit.http import get_json, get_text
from deltasci.audit.support import _CITE_TOKENS, _WORD_RE, salient_terms

OPENALEX_URL = "https://api.openalex.org/works"
ARXIV_URL = "http://export.arxiv.org/api/query"
PUBMED_ESEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
PUBMED_ESUMMARY = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
GITHUB_SEARCH = "https://api.github.com/search/repositories"

DEFAULT_SOURCES = ("openalex", "arxiv", "pubmed", "github")

# How many of the top topical terms actually go into the AND query sent to each source.
# Kept deliberately small: every extra conjunctive term shrinks recall, and a prior-art
# scan would rather over-retrieve and rank than return nothing. (Scoring still uses the
# richer term set returned by query_terms.)
QUERY_TERM_LIMIT = 4


@dataclass
class ScanHit:
    source: str  # openalex | arxiv | pubmed | github
    title: str
    authors: list[str]
    year: str
    venue: str
    url: str
    identifier: str
    snippet: str
    score: float = 0.0  # similarity to the query (term overlap), filled by scan()


@dataclass
class ScanReport:
    query: str
    terms: list[str]
    hits: list[ScanHit] = field(default_factory=list)
    counts: dict[str, int] = field(default_factory=dict)
    ok_sources: list[str] = field(default_factory=list)  # responded (even if 0 results)
    failed_sources: list[str] = field(default_factory=list)  # rate-limited / errored — coverage gap
    queries: list[str] = field(default_factory=list)  # every query actually issued


# --- query building + ranking (deterministic) ---------------------------------------
def _is_query_noise(term: str) -> bool:
    """Identifier-ish tokens pollute a free-text search: a bare PMID/accession/year is not a
    concept, and citation scaffolding ("pmid", "doi", "arxiv", "et", "al") is not a topic.
    Drop those while keeping real markers like CD8, IL-6, p53, GPT-4, COVID-19."""

    if term in _CITE_TOKENS:
        return True
    return term.isdigit() or bool(re.search(r"\d{4,}", term))


def query_terms(text: str, k: int = 6) -> list[str]:
    """The most *topical* salient terms from the input.

    Ranked by frequency, not length: a paper's real topic words (``learning``,
    ``skill``, ``reinforcement``, ``agent``) recur throughout the abstract/intro, while
    boilerplate (``state-of-the-art``) and paper-coined neologisms (``skillgenesis``,
    ``dual-uncertainty``) appear once or twice. The old length-ranking surfaced exactly
    those one-off compounds and starved the query of the words prior art actually shares.

    Only ``k`` terms (default 6, was 10): arXiv/PubMed treat spaces as AND, so every extra
    term shrinks recall — a 10-term conjunction including neologisms matches nothing but the
    paper itself. Six recurring topic words keep the query specific yet matchable.
    """

    salient = salient_terms(text)
    if not salient:
        return []
    counts: dict[str, int] = {}
    for m in _WORD_RE.finditer(text.lower()):
        w = m.group(0)
        if w in salient and not _is_query_noise(w):
            counts[w] = counts.get(w, 0) + 1
    if not counts:  # only marker/acronym tokens present → fall back to the salient set
        counts = {t: 1 for t in salient if not _is_query_noise(t)}
    # frequency desc, then longer (more specific) desc, then alpha for determinism
    return sorted(counts, key=lambda t: (counts[t], len(t), t), reverse=True)[:k]


def _score(query_terms_set: set[str], hit_text: str) -> float:
    if not query_terms_set:
        return 0.0
    ht = salient_terms(hit_text)
    return len(query_terms_set & ht) / len(query_terms_set)


def _openalex_abstract(inv: dict | None) -> str:
    """Reconstruct OpenAlex's inverted-index abstract into plain text."""

    if not inv:
        return ""
    positions: dict[int, str] = {}
    for word, idxs in inv.items():
        for i in idxs:
            positions[i] = word
    return " ".join(positions[i] for i in sorted(positions))[:600]


# --- per-source retrieval --------------------------------------------------------------
# These raise HTTPError on a network/rate-limit failure (so scan() can record the source as
# *failed* — a coverage gap that must not look like "nothing exists"). They return [] only
# for a genuinely empty result from a successful response.
def _query_openalex(q: str, n: int, timeout: float) -> list[ScanHit]:
    data = get_json(OPENALEX_URL, timeout=timeout, params={"search": q, "per-page": str(n), "mailto": "scan@deltasci.local"})
    hits = []
    for w in data.get("results") or []:
        title = (w.get("title") or "").strip()
        if not title:
            continue
        authors = [a.get("author", {}).get("display_name", "") for a in (w.get("authorships") or [])][:5]
        venue = (((w.get("primary_location") or {}).get("source") or {}).get("display_name")) or ""
        doi = w.get("doi") or ""
        hits.append(ScanHit("openalex", title, authors, str(w.get("publication_year") or ""), venue,
                            doi or w.get("id") or "", doi or w.get("id") or "", _openalex_abstract(w.get("abstract_inverted_index"))))
    return hits


def _query_arxiv(q: str, n: int, timeout: float) -> list[ScanHit]:
    # export.arxiv.org is reliably slow (often 20-40s). Give it one generous attempt
    # rather than the default exponential-backoff retries, which can balloon a single
    # scan into minutes. If it's too slow this run, it's recorded as a coverage gap —
    # and OpenAlex indexes arXiv preprints anyway, so its content is rarely truly lost.
    xml = get_text(ARXIV_URL, timeout=max(timeout, 25.0), params={"search_query": f"all:{q}", "max_results": str(n)}, retries=0)
    try:
        root = ET.fromstring(xml)
    except ET.ParseError:
        return []  # a 200 we couldn't parse → treat as empty, not a hard failure
    ns = {"a": "http://www.w3.org/2005/Atom"}
    hits = []
    for e in root.findall("a:entry", ns):
        title = " ".join((e.findtext("a:title", default="", namespaces=ns) or "").split())
        if not title:
            continue
        summary = " ".join((e.findtext("a:summary", default="", namespaces=ns) or "").split())[:600]
        authors = [(a.findtext("a:name", default="", namespaces=ns) or "") for a in e.findall("a:author", ns)][:5]
        idurl = e.findtext("a:id", default="", namespaces=ns) or ""
        m = re.search(r"abs/(.+?)(?:v\d+)?$", idurl)
        hits.append(ScanHit("arxiv", title, authors, (e.findtext("a:published", default="", namespaces=ns) or "")[:4],
                            "arXiv", idurl, m.group(1) if m else idurl, summary))
    return hits


def _query_pubmed(q: str, n: int, timeout: float) -> list[ScanHit]:
    s = get_json(PUBMED_ESEARCH, timeout=timeout, params={"db": "pubmed", "term": q, "retmax": str(n), "retmode": "json", "tool": "deltasci"})
    ids = ((s.get("esearchresult") or {}).get("idlist")) or []
    if not ids:
        return []
    summ = get_json(PUBMED_ESUMMARY, timeout=timeout, params={"db": "pubmed", "id": ",".join(ids), "retmode": "json", "tool": "deltasci"})
    res = summ.get("result") or {}
    hits = []
    for pid in ids:
        r = res.get(pid) or {}
        title = (r.get("title") or "").strip()
        if not title:
            continue
        authors = [a.get("name", "") for a in (r.get("authors") or [])][:5]
        venue = r.get("fulljournalname") or r.get("source") or ""
        hits.append(ScanHit("pubmed", title, authors, (r.get("pubdate") or "")[:4], venue,
                            f"https://pubmed.ncbi.nlm.nih.gov/{pid}/", f"PMID {pid}", ""))
    return hits


def _query_github(q: str, n: int, timeout: float) -> list[ScanHit]:
    data = get_json(GITHUB_SEARCH, timeout=timeout, params={"q": q, "per_page": str(n), "sort": "stars"})
    hits = []
    for r in data.get("items") or []:
        full = r.get("full_name", "")
        if not full:
            continue
        stars = r.get("stargazers_count", 0)
        venue = " · ".join(x for x in [f"{stars}★", r.get("language") or ""] if x)
        hits.append(ScanHit("github", full, [], "", venue, r.get("html_url", ""), full, r.get("description") or ""))
    return hits


_SOURCES = {"openalex": _query_openalex, "arxiv": _query_arxiv, "pubmed": _query_pubmed, "github": _query_github}


def scan(
    text: str = "",
    *,
    queries: list[str] | None = None,
    sources: list[str] | None = None,
    limit: int = 10,
    per_source: int = 8,
    timeout: float = 15.0,
    max_workers: int = 4,
    progress: "Callable[[str], None] | None" = None,
) -> ScanReport:
    """Retrieve and rank the closest existing works across public corpora. Deterministic.

    By default the query is built from `text` by topical term extraction. Pass `queries`
    to search explicit query strings instead — this is the primitive an agent (the SKILL.md
    grounding-layer path) uses to supply its own, smarter, LLM-written queries. Either way
    retrieval and term-overlap ranking are deterministic; an agent can rerank the hits.

    `progress`, if given, is called with short status lines as each source returns — so a
    15-40s network fan-out never *looks* frozen.
    """

    say = progress or (lambda _msg: None)
    chosen = [s for s in (sources or DEFAULT_SOURCES) if s in _SOURCES]

    explicit = [q for q in (s.strip() for s in (queries or [])) if q]
    if explicit:
        issue = explicit
        say("searching agent-supplied queries: " + " | ".join(issue))
    else:
        # Retrieve broad, rank narrow: query only the few most-topical terms (extra AND terms
        # — especially a paper's own coined method name — slash recall to near-zero).
        q = " ".join(query_terms(text, k=8)[:QUERY_TERM_LIMIT])
        issue = [q] if q.strip() else []
    if not issue:
        say("no usable query terms in the input")
        return ScanReport(query="", terms=[], hits=[], counts={})

    # Vocabulary used to score/rank what comes back — from the idea text, or the queries.
    terms = query_terms(text, k=8) if text else query_terms(" ".join(issue), k=8)

    say(f"searching {len(chosen)} sources ({', '.join(chosen)}) × {len(issue)} quer"
        f"{'y' if len(issue) == 1 else 'ies'} — one moment…")

    # One task per (source, query): a source counts as a coverage gap only if EVERY one of
    # its queries failed — a single slow query shouldn't blank out an otherwise-good source.
    raw: list[ScanHit] = []
    src_attempts: dict[str, int] = {s: 0 for s in chosen}
    src_failures: dict[str, int] = {s: 0 for s in chosen}
    jobs = [(s, qy) for s in chosen for qy in issue]
    done = 0
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(_SOURCES[s], qy, per_source, timeout): s for (s, qy) in jobs}
        for fut in as_completed(futures):
            src = futures[fut]
            src_attempts[src] += 1
            done += 1
            try:
                hits = fut.result()
                raw.extend(hits)
                say(f"[{done}/{len(jobs)}] {src}: {len(hits)} result(s)")
            except Exception:  # noqa: BLE001 - a flaky source must not sink the scan...
                src_failures[src] += 1
                say(f"[{done}/{len(jobs)}] {src}: a query didn't respond (slow/rate-limited)")

    ok_sources = [s for s in chosen if src_failures[s] < src_attempts[s]]
    failed_sources = [s for s in chosen if src_attempts[s] > 0 and src_failures[s] == src_attempts[s]]

    qset = set(terms)
    seen: set[str] = set()
    deduped: list[ScanHit] = []
    for h in raw:
        norm = re.sub(r"\W+", " ", h.title.lower()).strip()
        if not norm or norm in seen:
            continue
        seen.add(norm)
        h.score = round(_score(qset, f"{h.title} {h.snippet}"), 3)
        deduped.append(h)

    deduped.sort(key=lambda h: h.score, reverse=True)
    top = deduped[:limit]
    counts: dict[str, int] = {}
    for h in top:
        counts[h.source] = counts.get(h.source, 0) + 1
    return ScanReport(
        query=issue[0], terms=terms, hits=top, counts=counts,
        ok_sources=sorted(ok_sources), failed_sources=sorted(failed_sources),
        queries=issue,
    )


def render_scan_terminal(report: ScanReport) -> str:
    if not report.hits:
        msg = "No prior art found"
        if report.failed_sources:
            return msg + f" — but {', '.join(report.failed_sources)} did not respond (rate-limited?), so coverage is incomplete.\n"
        return msg + " (terms may be niche).\n"
    lines = [
        f"Prior-art scan · {len(report.hits)} closest works",
        "  " + "  ".join(f"{s}: {n}" for s, n in sorted(report.counts.items())),
        f"  query: {report.query[:90]}",
    ]
    if report.failed_sources:
        slow = ", ".join(report.failed_sources)
        note = f"  · {slow} was slow this run and was skipped"
        if "arxiv" in report.failed_sources and "openalex" in report.ok_sources:
            note += " (OpenAlex indexes arXiv preprints, so they're still represented above)"
        lines.append(note + ".")
    lines.append("")
    for i, h in enumerate(report.hits, 1):
        lines.append(f"{i:>2}. [{h.source}] {h.title[:96]}  ({h.score:.0%} overlap)")
        meta = " · ".join(x for x in [", ".join(h.authors[:2]), h.year, h.venue] if x)
        if meta:
            lines.append(f"     {meta}")
        if h.url:
            lines.append(f"     {h.url}")
    return "\n".join(lines).rstrip() + "\n"


def scan_payload(report: ScanReport) -> dict:
    return {
        "query": report.query,
        "queries": report.queries,
        "terms": report.terms,
        "counts": report.counts,
        "ok_sources": report.ok_sources,
        "failed_sources": report.failed_sources,
        "hits": [
            {
                "source": h.source, "title": h.title, "authors": h.authors, "year": h.year,
                "venue": h.venue, "url": h.url, "identifier": h.identifier,
                "snippet": h.snippet[:300], "score": h.score,
            }
            for h in report.hits
        ],
    }


__all__ = ["ScanHit", "ScanReport", "query_terms", "render_scan_terminal", "scan", "scan_payload"]
