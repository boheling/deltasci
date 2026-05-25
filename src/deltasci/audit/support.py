"""Deterministic claim-to-abstract *support* check.

Existence + metadata verifiers answer "is this a real paper?". The quote verifier
answers "does this verbatim quote appear in the abstract?". This auditor answers the
harder, more common question: **does the cited paper actually support the sentence it's
attached to?** — the failure where a claim about tumor-associated macrophages cites an
abstract about renal-pelvis adenocarcinoma (the BioIntel case), or a knowledge-graph-RL
claim cites a generic "ChatGPT opinion" paper (AutoResearchClaw #258).

It is **deterministic** (salient-term overlap, no LLM, no API key beyond the PubMed
fetch the project already does), so `deltasci verify` works with zero provider keys —
directly answering the ecosystem's #1 DX complaint (vendor lock-in). It is also
**conservative**: it only fires "unsupported" when overlap is near-zero, reports
``medium`` confidence (it is a heuristic, not an entailment proof), and abstains
(``unverifiable``) on short claims it cannot fairly judge.

A future, opt-in LLM entailment grade can layer on top — but only ever consuming the
freshly-fetched abstract, never the model's training memory (see `Auditor` docstring).
"""

from __future__ import annotations

import re
from typing import Iterable

from deltasci.audit.base import AuditFinding, Auditor
from deltasci.audit.extractor import Identifier
from deltasci.audit.quotes.verifier import fetch_abstract, find_quotes

# Overlap thresholds (fraction of the claim's salient terms also present in the abstract).
SUPPORTED_AT = 0.30
UNSUPPORTED_BELOW = 0.12
MIN_SALIENT_TERMS = 3  # below this we cannot judge fairly → abstain

_STOPWORDS = frozenset(
    """
    about above after again against algorithm all also among analysis approach are based
    because been before being below between both but can could data demonstrate
    demonstrated different does down during each effect effects evidence find finding
    findings from further has have here high higher however into its itself jhep level
    levels low lower made many measure measured method methods more most much novel only
    other our over patients propose proposed result results same show showed shown significant
    significantly some study studies such than that the their them then there these they this
    those through using very was were what when where which while will with within without
    would your
    """.split()
)

_WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9\-]{2,}")
_TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9\-]*")

# The identifier and citation scaffolding must never count as shared terms: the efetch
# abstract text echoes the PMID, so leaving "pmid"/"35562209" in the claim's term set
# would inflate overlap and mask a wrong-paper miscitation.
_CITE_TOKENS = frozenset({"pmid", "doi", "arxiv", "pubmed", "preprint", "et", "al"})


def _is_marker(tok: str) -> bool:
    """Acronyms / gene-or-marker names carry most of a biomedical claim's specificity
    (TFE3, AML, HLA-DR, CD8, IL-6). A token qualifies if it has a digit or 2+ uppercase
    letters — which excludes ordinary sentence-initial words like 'The' or 'Tumor'."""

    if len(tok) < 2:
        return False
    return any(c.isdigit() for c in tok) or sum(1 for c in tok if c.isupper()) >= 2


def salient_terms(text: str) -> set[str]:
    """Content-bearing terms: lowercased words (len>=3, non-stopword) plus acronym/marker tokens."""

    terms: set[str] = set()
    for m in _WORD_RE.finditer(text.lower()):
        w = m.group(0)
        if w not in _STOPWORDS:
            terms.add(w)
    for tok in _TOKEN_RE.findall(text):
        if _is_marker(tok):
            terms.add(tok.lower())
    return terms


class ClaimSupportAuditor(Auditor):
    """Flag claims whose salient terms are absent from the cited paper's abstract.

    PubMed only in v1 (reuses the project's existing efetch path). Skips claims that
    carry a verbatim quote — the :class:`QuoteInAbstractAuditor` owns those.
    """

    name = "claim_support"

    def __init__(self, timeout: float = 10.0) -> None:
        self.timeout = timeout

    def can_audit(self, target: object) -> bool:
        return (
            isinstance(target, dict)
            and target.get("identifier")
            and target["identifier"].kind == "pmid"
            and bool(target.get("claim_text"))
            and not find_quotes(target["claim_text"])  # quoted claims → QuoteInAbstractAuditor
        )

    def audit(self, target: dict) -> AuditFinding:
        identifier: Identifier = target["identifier"]
        claim_text: str = target["claim_text"]

        abstract = fetch_abstract(identifier.value, timeout=self.timeout)
        if abstract is None:
            return AuditFinding(
                target_kind="support",
                target_summary=claim_text[:160],
                auditor_name=self.name,
                status="skipped",
                fetched_metadata={"pmid": identifier.value},
                mismatch_reasons=[f"could not fetch abstract for PMID {identifier.value}"],
                confidence="low",
            )

        claim_terms = salient_terms(claim_text)
        ident_tokens = set(re.findall(r"[a-z0-9]+", f"{identifier.value} {identifier.raw}".lower()))
        claim_terms -= ident_tokens | _CITE_TOKENS
        if len(claim_terms) < MIN_SALIENT_TERMS:
            return AuditFinding(
                target_kind="support",
                target_summary=claim_text[:160],
                auditor_name=self.name,
                status="unverifiable",
                fetched_metadata={"pmid": identifier.value, "reason": "claim too short to assess support"},
                confidence="low",
            )

        abstract_terms = salient_terms(abstract) - _CITE_TOKENS
        if len(abstract_terms) < 5:
            # No usable abstract (e.g. an efetch stub for a nonexistent PMID). Absence of
            # an abstract is not evidence the paper is wrong — abstain rather than flag.
            return AuditFinding(
                target_kind="support",
                target_summary=claim_text[:160],
                auditor_name=self.name,
                status="unverifiable",
                fetched_metadata={"pmid": identifier.value, "reason": "no usable abstract to assess support"},
                confidence="low",
            )
        overlap = claim_terms & abstract_terms
        ratio = len(overlap) / len(claim_terms)
        meta = {
            "pmid": identifier.value,
            "overlap_ratio": round(ratio, 3),
            "overlap_terms": sorted(overlap)[:20],
            "claim_terms": sorted(claim_terms)[:20],
            "abstract_excerpt": abstract[:400],
        }

        if ratio >= SUPPORTED_AT:
            return AuditFinding(
                target_kind="support",
                target_summary=claim_text[:160],
                auditor_name=self.name,
                status="verified",
                fetched_metadata=meta,
                confidence="medium",
            )
        if ratio < UNSUPPORTED_BELOW:
            return AuditFinding(
                target_kind="support",
                target_summary=claim_text[:160],
                auditor_name=self.name,
                status="mismatch",
                fetched_metadata=meta,
                mismatch_reasons=[
                    f"claim shares almost no salient terms with the title/abstract of PMID "
                    f"{identifier.value} (overlap {ratio:.0%}) — likely citing the wrong paper"
                ],
                confidence="medium",
            )
        return AuditFinding(
            target_kind="support",
            target_summary=claim_text[:160],
            auditor_name=self.name,
            status="unverifiable",
            fetched_metadata={**meta, "reason": "inconclusive topical overlap"},
            confidence="low",
        )


__all__: Iterable[str] = ("ClaimSupportAuditor", "salient_terms")
