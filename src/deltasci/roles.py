"""Two roles: DomainScientist and MLEngineer.

Each role has a system prompt, a per-round user prompt, and a `repair` mode
used when grounding violations are detected.
"""

from __future__ import annotations

from dataclasses import dataclass

from deltasci.grounding import format_violations_for_repair
from deltasci.llm.base import LLMAdapter, Message
from deltasci.packs import DomainPack
from deltasci.transcript import RoleName, Transcript

GROUNDING_INSTRUCTIONS = """
You must mark every factual statement with one of three first-class tags. The
goal is to be honest about what you know reliably, what you're hedging on, and
what falls outside your training distribution and therefore needs a researcher.

================================================================================
TAG 1 — [CLAIM type=<TYPE> coverage=<COVERAGE> source="<CITATION>"]<text>[/CLAIM]
================================================================================

Use this for any factual claim you are willing to assert.

`type` is exactly one of:
- published-evidence    (peer-reviewed paper, preprint with DOI, dataset paper)
- established-guideline (recognized guideline body, standard, regulation)
- engineering-precedent (open-source repo, benchmark, reference implementation)
- observation           (your own analysis or domain reasoning, not a citation)

`coverage` is exactly one of:
- well-covered : You can recall this from multiple independent textbook /
                 review-level sources. You're confident in the specifics.
- sparse       : You have signal but might confabulate dates, names, or
                 specific numbers. You'll cite only verbatim and hedge details.

`source` is required for the first three types and may be empty for `observation`.

DO NOT use coverage="uncovered" on a CLAIM. If you think a claim sits outside
your training distribution, emit a KNOWLEDGE_GAP instead.

================================================================================
TAG 2 — [KNOWLEDGE_GAP category=<CATEGORY>]<question for the researcher>[/KNOWLEDGE_GAP]
================================================================================

Use this WHENEVER you would otherwise be tempted to fabricate. AI models train
on the open web, which under-represents:

- lab-tribal-knowledge              ("everyone in this lab does X but it's not written down")
- paywalled-or-non-OA               (subscription journals, behind paywalls)
- non-english-literature            (significant work in non-English communities)
- niche-subfield                    (rarely cited, thin training signal)
- unpublished-or-pilot-data         (the researcher's own data)
- patent-or-clinical-practice       (under-indexed corpora)
- novel-cross-disciplinary-connection (both ends well-covered, the link is not)
- other

Emit a KNOWLEDGE_GAP rather than guess. The researcher will fill these in.

================================================================================
TAG 3 — [NOVEL_SYNTHESIS rationale="<one-line>"]<proposed connection>[/NOVEL_SYNTHESIS]
================================================================================

Use this when you are *making a leap* — combining multiple well-covered facts
into a hypothesis or connection that no source explicitly states. This is not
fabrication; it is the creative step at the heart of hypothesis generation.
But it must be marked, not dressed up as a citation.

================================================================================

A round with zero KNOWLEDGE_GAPs and zero NOVEL_SYNTHESES is suspect — it
suggests you're claiming complete certainty about everything, which is itself
a hallucination signal.
""".strip()


DOMAIN_SYSTEM_TEMPLATE = """\
You are a senior {display_name} researcher participating in a structured 4-round
co-reasoning dialogue with an ML engineer. Your job is to ground the research
idea in domain knowledge: mechanism, prior literature, established practice,
and falsifiable predictions.

Your domain lens:
---
{lens}
---

{grounding}
"""


ENGINEER_SYSTEM = """\
You are a senior machine-learning engineer participating in a structured 4-round
co-reasoning dialogue with a domain scientist. Your job is to translate the
domain framing into a concrete, technically feasible plan: data representation,
model class, training protocol, evaluation, and risks.

You do not invent domain facts; you respond to the domain expert and propose
methods with engineering precedent.

{grounding}
""".strip()


ROUND_USER_PROMPT = {
    "domain_r1": (
        "Round 1 — Domain framing.\n"
        "Research idea: {idea}\n\n"
        "Provide:\n"
        "1. The disease/system/phenomenon mechanism behind this idea.\n"
        "2. The unmet need this addresses.\n"
        "3. Prior work establishing the mechanism.\n"
        "4. Practical constraints (data access, ethics, reproducibility).\n"
        "Use CLAIM tags for things you know; KNOWLEDGE_GAP for things you can't reliably know; "
        "NOVEL_SYNTHESIS for connections you are proposing."
    ),
    "engineer_r1": (
        "Round 1 — Engineering analysis.\n"
        "Respond to the domain scientist's framing with:\n"
        "1. Optimal data representation given the mechanism.\n"
        "2. ML paradigm and why it fits (vs alternatives).\n"
        "3. Existing implementations or benchmarks (cite repos).\n"
        "4. Computational cost and feasibility.\n"
        "5. Top technical risks.\n"
        "Use CLAIM, KNOWLEDGE_GAP, and NOVEL_SYNTHESIS tags as appropriate."
    ),
    "domain_r2": (
        "Round 2 — Domain refinement.\n"
        "Respond to the engineer's plan:\n"
        "1. Does the proposed approach capture the right domain features? What's missing?\n"
        "2. Are the proposed metrics meaningful in this domain? Suggest better ones.\n"
        "3. Domain-specific improvements (data augmentation, loss design, evaluation framing).\n"
        "4. One concrete falsifiable prediction this hypothesis should commit to.\n"
        "Use CLAIM, KNOWLEDGE_GAP, and NOVEL_SYNTHESIS tags as appropriate."
    ),
    "engineer_r2": (
        "Round 2 — Technical integration.\n"
        "Integrate the domain refinements:\n"
        "1. Revised architecture and training strategy.\n"
        "2. Mathematical formulation of the key method (formulas tied to references).\n"
        "3. Concrete implementation plan (dataset, model, training, evaluation).\n"
        "4. Quantitative expected outcomes vs baselines.\n"
        "Use CLAIM, KNOWLEDGE_GAP, and NOVEL_SYNTHESIS tags as appropriate."
    ),
}


def transcript_so_far(transcript: Transcript) -> str:
    if not transcript.rounds:
        return "(no prior rounds)"
    parts = []
    for entry in transcript.rounds:
        parts.append(f"### {entry.kind} ({entry.role})\n{entry.text.strip()}\n")
        for r in transcript.redirects_after(entry.kind):
            parts.append(
                f"### researcher redirect after {entry.kind}\n"
                f"The researcher reviewed the round above and provided this feedback:\n\n"
                f"> {r.feedback}\n\n"
                f"You MUST address this feedback explicitly in your response.\n"
            )
    return "\n".join(parts)


@dataclass
class RoleOutput:
    text: str


class Role:
    name: RoleName

    def __init__(self, llm: LLMAdapter, pack: DomainPack):
        self.llm = llm
        self.pack = pack

    def system_prompt(self) -> str:  # pragma: no cover - overridden
        raise NotImplementedError

    def run(self, round_kind: str, idea: str, transcript: Transcript) -> RoleOutput:
        user = ROUND_USER_PROMPT[round_kind].format(idea=idea)
        prior = transcript_so_far(transcript)
        if prior != "(no prior rounds)":
            user = f"Prior rounds:\n\n{prior}\n\n---\n\n{user}"
        text = self.llm.complete(system=self.system_prompt(), messages=[Message("user", user)])
        return RoleOutput(text=text)

    def repair(self, prior_text: str, violations_msg: str) -> RoleOutput:
        repair_user = (
            f"{violations_msg}\n\n"
            f"Here is your previous response:\n---\n{prior_text}\n---\n\n"
            f"Re-emit the response with every claim properly tagged."
        )
        text = self.llm.complete(system=self.system_prompt(), messages=[Message("user", repair_user)])
        return RoleOutput(text=text)


class DomainScientist(Role):
    name: RoleName = "domain_scientist"

    def system_prompt(self) -> str:
        return DOMAIN_SYSTEM_TEMPLATE.format(
            display_name=self.pack.display_name,
            lens=self.pack.lens.strip(),
            grounding=GROUNDING_INSTRUCTIONS,
        )


class MLEngineer(Role):
    name: RoleName = "ml_engineer"

    def system_prompt(self) -> str:
        return ENGINEER_SYSTEM.format(grounding=GROUNDING_INSTRUCTIONS)


def role_for_round(kind: str, llm: LLMAdapter, pack: DomainPack) -> Role:
    if kind.startswith("domain_"):
        return DomainScientist(llm=llm, pack=pack)
    if kind.startswith("engineer_"):
        return MLEngineer(llm=llm, pack=pack)
    raise ValueError(f"Unknown round kind: {kind!r}")


__all__ = [
    "DomainScientist",
    "MLEngineer",
    "Role",
    "RoleOutput",
    "role_for_round",
    "GROUNDING_INSTRUCTIONS",
]


def format_violations(violations) -> str:  # backward-friendly alias
    return format_violations_for_repair(violations)
