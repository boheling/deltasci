"""CoReasoner — orchestrates the dialogue, synthesis, protocol, risks, and audit."""

from __future__ import annotations

from dataclasses import dataclass

from deltasci import grounding as grounding_mod
from deltasci.audit import AuditFinding, AuditReport, MultiLayerAuditor
from deltasci.audit.cache import AuditCache
from deltasci.challenger import ChallengeReport, run_challenge
from deltasci.config import Config
from deltasci.hypothesis import EvidenceItem, GroundedHypothesis
from deltasci.interactive import (
    InteractionHandler,
    NullInteractionHandler,
    ResearcherRedirect,
    gate_eligible,
)
from deltasci.llm.base import LLMAdapter
from deltasci.packs import DomainPack
from deltasci.protocol import (
    ExperimentPlan,
    RiskRegister,
    assemble_protocol,
    assemble_risks,
)
from deltasci.roles import role_for_round
from deltasci.synthesis import assemble
from deltasci.transcript import RoundEntry, Transcript

ROUND_PLAN_4 = ["domain_r1", "engineer_r1", "domain_r2", "engineer_r2"]
ROUND_PLAN_6 = ["domain_r1", "engineer_r1", "domain_r2", "engineer_r2", "domain_r3", "engineer_r3"]


@dataclass
class RoundCounts:
    kind: str
    claims: int
    knowledge_gaps: int
    novel_syntheses: int
    violations: int


@dataclass
class GroundingSummary:
    total_claims: int
    total_knowledge_gaps: int
    total_novel_syntheses: int
    total_violations: int
    by_round: list[RoundCounts]

    def to_dict(self) -> dict:
        return {
            "total_claims": self.total_claims,
            "total_knowledge_gaps": self.total_knowledge_gaps,
            "total_novel_syntheses": self.total_novel_syntheses,
            "total_violations": self.total_violations,
            "by_round": [
                {
                    "kind": rc.kind,
                    "claims": rc.claims,
                    "knowledge_gaps": rc.knowledge_gaps,
                    "novel_syntheses": rc.novel_syntheses,
                    "violations": rc.violations,
                }
                for rc in self.by_round
            ],
        }


@dataclass
class Result:
    transcript: Transcript
    hypothesis: GroundedHypothesis
    grounding_summary: GroundingSummary
    audit_report: AuditReport
    plan: ExperimentPlan | None = None
    risks: RiskRegister | None = None
    challenge: ChallengeReport | None = None


class CoReasoner:
    """Run a structured 4-round (or 6-round) co-reasoning session, then synthesize hypothesis, protocol, risks, and (optionally) an adversarial challenge — all auditable."""

    def __init__(
        self,
        pack: DomainPack,
        llm: LLMAdapter,
        config: Config | None = None,
        auditor: MultiLayerAuditor | None = None,
        challenger_llm: LLMAdapter | None = None,
        interaction_handler: InteractionHandler | None = None,
    ) -> None:
        self.pack = pack
        self.llm = llm
        self.config = config or Config()
        self._auditor = auditor
        self._challenger_llm = challenger_llm  # if None, falls back to self.llm
        self._interaction = interaction_handler or NullInteractionHandler()

    def _round_plan(self) -> list[str]:
        if self.config.num_rounds == 4:
            return ROUND_PLAN_4
        if self.config.num_rounds == 6:
            return ROUND_PLAN_6
        raise ValueError(f"Unsupported num_rounds={self.config.num_rounds}; expected 4 or 6.")

    def run(self, idea: str) -> Result:
        from deltasci import __version__ as deltasci_version

        transcript = Transcript(idea=idea, pack_name=self.pack.name)
        by_round: list[RoundCounts] = []

        for kind in self._round_plan():
            role = role_for_round(kind, llm=self.llm, pack=self.pack)
            entry, report = self._run_one_round(role=role, kind=kind, idea=idea, transcript=transcript)
            transcript.append(entry, report=report)
            counts = RoundCounts(
                kind=kind,
                claims=len(report.items),
                knowledge_gaps=len(report.knowledge_gaps),
                novel_syntheses=len(report.novel_syntheses),
                violations=len(report.violations),
            )
            by_round.append(counts)

            # Interactive gate after eligible rounds (domain_r1, domain_r2 in v0.2.1).
            if self.config.interactive and gate_eligible(kind):
                self._handle_gate(kind=kind, transcript=transcript, role=role, idea=idea, by_round=by_round)

        hypothesis = assemble(
            transcript=transcript,
            pack=self.pack,
            llm=self.llm,
            deltasci_version=deltasci_version,
            require_falsifiability=self.config.require_falsifiability,
            require_epistemic_humility=self.config.require_epistemic_humility,
        )

        summary = GroundingSummary(
            total_claims=sum(rc.claims for rc in by_round),
            total_knowledge_gaps=sum(rc.knowledge_gaps for rc in by_round),
            total_novel_syntheses=sum(rc.novel_syntheses for rc in by_round),
            total_violations=sum(rc.violations for rc in by_round),
            by_round=by_round,
        )

        plan: ExperimentPlan | None = None
        risks: RiskRegister | None = None
        challenge: ChallengeReport | None = None

        if self.config.generate_protocol:
            plan = assemble_protocol(hypothesis=hypothesis, transcript=transcript, llm=self.llm)
        if self.config.generate_risks and plan is not None:
            risks = assemble_risks(
                hypothesis=hypothesis, plan=plan, transcript=transcript, llm=self.llm
            )
        if self.config.run_challenge:
            challenger_llm = self._challenger_llm or self.llm
            challenge = run_challenge(
                hypothesis=hypothesis,
                plan=plan,
                risks=risks,
                transcript=transcript,
                llm=challenger_llm,
            )

        # Audit pillar runs over the full corpus of citations: hypothesis evidence,
        # protocol method citations, risk-register counter-evidence, and challenger
        # evidence — augmentations A and B from the v0.2 plan.
        audit_report = self._run_audit(
            hypothesis=hypothesis,
            plan=plan,
            risks=risks,
            challenge=challenge,
        )

        return Result(
            transcript=transcript,
            hypothesis=hypothesis,
            grounding_summary=summary,
            audit_report=audit_report,
            plan=plan,
            risks=risks,
            challenge=challenge,
        )

    def _run_one_round(self, role, kind, idea, transcript):
        """Run a single round + grounding extraction + repair attempts."""

        output = role.run(round_kind=kind, idea=idea, transcript=transcript)
        report = grounding_mod.extract_signals(output.text)
        grounding_mod.check_against_rules(report, self.pack.evidence_rules)

        attempts = 0
        while report.violations and attempts < self.config.max_repair_attempts and self.config.grounding_strictness == "high":
            violations_msg = grounding_mod.format_violations_for_repair(report.violations)
            output = role.repair(prior_text=output.text, violations_msg=violations_msg)
            report = grounding_mod.extract_signals(output.text)
            grounding_mod.check_against_rules(report, self.pack.evidence_rules)
            attempts += 1

        entry = RoundEntry(
            role=role.name,
            kind=kind,  # type: ignore[arg-type]
            text=output.text,
            evidence=list(report.items),
            knowledge_gaps=list(report.knowledge_gaps),
            novel_syntheses=list(report.novel_syntheses),
            violations_remaining=len(report.violations),
        )
        return entry, report

    def _handle_gate(self, *, kind, transcript, role, idea, by_round) -> None:
        """Loop on InteractionHandler decisions until approve / redirect."""

        from deltasci.interactive import InteractionDecision  # local for clarity

        while True:
            entry = transcript.rounds[-1]
            decision = self._interaction.gate(kind=kind, entry=entry, transcript=transcript)
            if decision.action == "approve":
                return
            if decision.action == "redirect":
                if decision.feedback.strip():
                    transcript.redirects.append(
                        ResearcherRedirect(after_round_kind=kind, feedback=decision.feedback)
                    )
                return
            if decision.action == "re_do":
                # Pop the last round so prior-context for the re-run doesn't
                # include the rejected attempt, then regenerate and push.
                popped_entry = transcript.rounds.pop()
                popped_report = transcript.grounding_reports.pop() if transcript.grounding_reports else None
                try:
                    new_entry, new_report = self._run_one_round(
                        role=role, kind=kind, idea=idea, transcript=transcript
                    )
                except Exception:
                    transcript.rounds.append(popped_entry)
                    if popped_report is not None:
                        transcript.grounding_reports.append(popped_report)
                    raise
                transcript.append(new_entry, report=new_report)
                by_round[-1] = RoundCounts(
                    kind=kind,
                    claims=len(new_report.items),
                    knowledge_gaps=len(new_report.knowledge_gaps),
                    novel_syntheses=len(new_report.novel_syntheses),
                    violations=len(new_report.violations),
                )
                continue
            if decision.action == "audit_now":
                partial_audit = self._run_partial_audit(transcript)
                self._interaction.display_audit(partial_audit)
                continue
            # Unknown action — fail loudly rather than silently approve.
            raise ValueError(f"unknown InteractionDecision action: {decision.action!r}")

    def _run_partial_audit(self, transcript: Transcript) -> AuditReport:
        """Run audit over the evidence collected so far (used by audit-now interactive)."""

        if not self.config.audit_enabled:
            return AuditReport(skipped=True, skipped_reason="audit disabled")
        auditor = self._auditor
        if auditor is None:
            cache = AuditCache(self.config.audit_cache_path) if self.config.audit_cache_path else AuditCache()
            auditor = MultiLayerAuditor(cache=cache)
        partial_evidence: list[EvidenceItem] = []
        for r in transcript.rounds:
            partial_evidence.extend(r.evidence)
        return auditor.audit(partial_evidence)

    def _run_audit(
        self,
        hypothesis: GroundedHypothesis,
        plan: ExperimentPlan | None,
        risks: RiskRegister | None,
        challenge: ChallengeReport | None,
    ) -> AuditReport:
        if not self.config.audit_enabled:
            return AuditReport(skipped=True, skipped_reason="audit_enabled=False (likely --no-audit)")
        auditor = self._auditor
        if auditor is None:
            cache = AuditCache(self.config.audit_cache_path) if self.config.audit_cache_path else AuditCache()
            auditor = MultiLayerAuditor(cache=cache)

        targets: list[EvidenceItem] = list(hypothesis.evidence_trail)

        # Augmentation A: protocol + risks citations also flow through audit.
        if plan is not None:
            for step in plan.steps:
                for src in step.method_citations:
                    item = _citation_to_evidence(src, kind="protocol-method")
                    if item is not None:
                        targets.append(item)
        if risks is not None:
            for item in risks.items:
                for src in item.counter_evidence_citations:
                    item = _citation_to_evidence(src, kind="risk-counter-evidence")
                    if item is not None:
                        targets.append(item)

        # Augmentation B: challenger citations also flow through audit. Otherwise
        # we've added a second model that can hallucinate just like the first.
        if challenge is not None:
            for finding in challenge.findings:
                for src in finding.evidence_citations:
                    item = _citation_to_evidence(src, kind="challenge-evidence")
                    if item is not None:
                        targets.append(item)

        report = auditor.audit(targets)

        # Annotate findings with where they came from, so the renderer can group them.
        # (We don't change the schema; we rely on target_summary which already carries
        # the source string.)
        return report


def _citation_to_evidence(source: str, kind: str) -> EvidenceItem | None:
    """Wrap a raw source string in a minimal EvidenceItem the auditor can ingest.

    Returns None for empty sources (nothing for the auditor to do). For non-empty
    sources we use type="observation" so the per-pack source-pattern rules
    (which apply to published-evidence/engineering-precedent) don't reject
    free-form method-citation strings — the auditor still extracts PMIDs/DOIs
    and runs verifiers regardless of type.
    """

    if not source.strip():
        return None
    return EvidenceItem(
        claim=f"[{kind}] {source[:120]}",
        type="observation",
        source=source,
        coverage="sparse",
    )
