---
title: DeltaScience Verifier
emoji: 🔬
colorFrom: green
colorTo: gray
sdk: docker
app_port: 7860
pinned: false
license: mit
---

# DeltaScience verifier (API)

Independent, deterministic citation verification — **no LLM, no API key**.

`POST /verify` with `{"text": "...", "checkSupport": true}` and every PMID / DOI / arXiv ID /
GitHub repo in the text is checked against the real record (Crossref · PubMed · OpenAlex ·
arXiv); references with no inline identifier are resolved by Crossref **title search**; and the
response includes an honest **coverage** report (what was checked, what was recovered by title,
what could not be resolved at all).

Returns the same JSON the `deltasci verify --json` CLI emits:
`{ summary, verdicts, findings[], coverage }`.

Calls happen server-side, so unlike a browser-only verifier this can use PubMed (the
claim-to-abstract *support* check) and arXiv too.
