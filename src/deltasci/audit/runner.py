"""MultiLayerAuditor — orchestrates verifiers across all evidence in a transcript."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Iterable

from deltasci.audit.base import AuditFinding, AuditReport, Auditor
from deltasci.audit.cache import AuditCache
from deltasci.audit.citations.arxiv import ArxivAuditor
from deltasci.audit.citations.crossref import CrossrefAuditor
from deltasci.audit.citations.openalex import OpenAlexAuditor
from deltasci.audit.citations.pubmed import PubMedAuditor
from deltasci.audit.citations.semscholar import SemanticScholarAuditor
from deltasci.audit.datasets.geo import GEOAuditor
from deltasci.audit.extractor import Identifier, extract_identifiers
from deltasci.audit.quotes.verifier import QuoteInAbstractAuditor
from deltasci.audit.repos.github import GitHubAuditor
from deltasci.audit.repos.huggingface import HuggingFaceAuditor


@dataclass
class _AuditTarget:
    """A unit of work for the audit runner."""

    identifier: Identifier
    claim_source: str
    claim_text: str
    role_for_quote_check: bool = True

    def as_dict(self) -> dict:
        return {
            "identifier": self.identifier,
            "claim_source": self.claim_source,
            "claim_text": self.claim_text,
        }


class MultiLayerAuditor:
    """Runs every applicable verifier against every identifier in a transcript.

    PubMed and OpenAlex both handle PMIDs — when both verify, a 'verified' result
    from either is enough; a 'mismatch' from either flags the claim. (We err
    toward "more verifiers = more confidence", but a single mismatch is loud.)
    """

    def __init__(
        self,
        auditors: Iterable[Auditor] | None = None,
        cache: AuditCache | None = None,
        max_workers: int = 4,
    ) -> None:
        self.auditors: list[Auditor] = list(auditors) if auditors else _default_auditors()
        self.cache = cache if cache is not None else AuditCache()
        self.max_workers = max_workers

    def audit(
        self,
        evidence_items: Iterable,  # iterable of EvidenceItem
    ) -> AuditReport:
        targets = list(_collect_targets(evidence_items))
        if not targets:
            return AuditReport(findings=[])

        findings: list[AuditFinding] = []

        # Resolve cache hits up front; collect misses to dispatch.
        misses: list[tuple[Auditor, _AuditTarget]] = []
        for target in targets:
            for auditor in self.auditors:
                if not auditor.can_audit(target.as_dict()):
                    continue
                cached = self.cache.get(auditor.name, target.identifier.kind, target.identifier.value)
                if cached is not None:
                    findings.append(cached)
                else:
                    misses.append((auditor, target))

        # Run uncached audits in parallel.
        if misses:
            with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
                futures = {pool.submit(_run_one, auditor, target): (auditor, target) for auditor, target in misses}
                for future in as_completed(futures):
                    auditor, target = futures[future]
                    finding = future.result()
                    findings.append(finding)
                    self.cache.put(auditor.name, target.identifier.kind, target.identifier.value, finding)

        self.cache.flush()
        return AuditReport(findings=findings)


def _run_one(auditor: Auditor, target: _AuditTarget) -> AuditFinding:
    try:
        return auditor.audit(target.as_dict())
    except Exception as exc:  # noqa: BLE001 - never crash the run
        return AuditFinding(
            target_kind="citation",
            target_summary=target.claim_source,
            auditor_name=auditor.name,
            status="skipped",
            mismatch_reasons=[f"audit raised unexpectedly: {exc!r}"],
            confidence="low",
        )


def _collect_targets(evidence_items: Iterable) -> Iterable[_AuditTarget]:
    """Walk EvidenceItems and yield one target per identifier found."""

    seen: set[tuple[str, str, str]] = set()
    for ev in evidence_items:
        idents = extract_identifiers(ev.source)
        # Also scan the claim text — sometimes the AI puts the PMID in the claim body.
        idents = list({(i.kind, i.value): i for i in (idents + extract_identifiers(ev.claim))}.values())
        for ident in idents:
            key = (ident.kind, ident.value, ev.source)
            if key in seen:
                continue
            seen.add(key)
            yield _AuditTarget(identifier=ident, claim_source=ev.source, claim_text=ev.claim)


def _default_auditors() -> list[Auditor]:
    return [
        PubMedAuditor(),
        CrossrefAuditor(),
        OpenAlexAuditor(),
        ArxivAuditor(),
        SemanticScholarAuditor(),
        GitHubAuditor(),
        HuggingFaceAuditor(),
        GEOAuditor(),
        QuoteInAbstractAuditor(),
    ]


def default_auditor() -> MultiLayerAuditor:
    return MultiLayerAuditor()
