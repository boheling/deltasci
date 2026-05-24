from __future__ import annotations

import pytest

from deltasci.config import Config
from deltasci.engine import CoReasoner
from deltasci.synthesis import SynthesisError


def test_full_4round_run_with_scripted_llm(biomed_pack, scripted_llm):
    config = Config(num_rounds=4, grounding_strictness="high", require_falsifiability=True, audit_enabled=False, generate_protocol=False, generate_risks=False, run_challenge=False)
    reasoner = CoReasoner(pack=biomed_pack, llm=scripted_llm, config=config)
    result = reasoner.run(idea="Predict a thing from a thing.")

    assert len(result.transcript.rounds) == 4
    assert result.hypothesis.falsifiability.threshold
    assert result.hypothesis.feasibility_scores.overall > 0
    for axis in biomed_pack.scoring_rubric.axes:
        assert axis in result.hypothesis.feasibility_scores.scores
    assert result.grounding_summary.total_claims > 0
    assert result.grounding_summary.total_violations == 0
    # Epistemic humility gate is satisfied by the fixture
    assert result.grounding_summary.total_knowledge_gaps >= 1
    assert result.grounding_summary.total_novel_syntheses >= 1
    assert result.hypothesis.epistemic_summary.knowledge_gap_count >= 1
    assert result.hypothesis.epistemic_summary.novel_synthesis_count >= 1


def test_synthesis_refuses_when_falsifiability_missing(biomed_pack):
    from deltasci.llm.mock import MockLLM

    rounds_script = [
        '[CLAIM type=observation coverage=well-covered source=""]ok[/CLAIM] '
        '[KNOWLEDGE_GAP category=other]?[/KNOWLEDGE_GAP] '
        '[NOVEL_SYNTHESIS]x[/NOVEL_SYNTHESIS]'
    ] * 4
    bad_synthesis = '{"error": "no_falsifiable_clause", "reason": "transcript lacked a measurable threshold"}'
    llm = MockLLM(responses=rounds_script + [bad_synthesis])

    config = Config(num_rounds=4, require_falsifiability=True, audit_enabled=False, generate_protocol=False, generate_risks=False, run_challenge=False)
    reasoner = CoReasoner(pack=biomed_pack, llm=llm, config=config)
    with pytest.raises(SynthesisError):
        reasoner.run(idea="vague idea")


def test_synthesis_rejects_invalid_json(biomed_pack):
    from deltasci.llm.mock import MockLLM

    rounds_script = [
        '[CLAIM type=observation coverage=well-covered source=""]ok[/CLAIM] '
        '[KNOWLEDGE_GAP category=other]?[/KNOWLEDGE_GAP] '
        '[NOVEL_SYNTHESIS]x[/NOVEL_SYNTHESIS]'
    ] * 4
    llm = MockLLM(responses=rounds_script + ["not json at all"])

    config = Config(num_rounds=4, audit_enabled=False, generate_protocol=False, generate_risks=False, run_challenge=False)
    reasoner = CoReasoner(pack=biomed_pack, llm=llm, config=config)
    with pytest.raises(SynthesisError):
        reasoner.run(idea="vague idea")


def test_epistemic_humility_gate_refuses_when_no_gaps_or_syntheses(biomed_pack, scripted_synthesis_response):
    """A transcript with zero knowledge gaps AND zero novel syntheses must be refused."""

    from deltasci.llm.mock import MockLLM

    rounds_script = ['[CLAIM type=observation coverage=well-covered source=""]ok[/CLAIM]'] * 4
    llm = MockLLM(responses=rounds_script + [scripted_synthesis_response])

    config = Config(num_rounds=4, require_epistemic_humility=True, audit_enabled=False, generate_protocol=False, generate_risks=False, run_challenge=False)
    reasoner = CoReasoner(pack=biomed_pack, llm=llm, config=config)
    with pytest.raises(SynthesisError, match="hallucination signal"):
        reasoner.run(idea="suspicious idea")


def test_epistemic_humility_can_be_disabled(biomed_pack, scripted_synthesis_response):
    """With require_epistemic_humility=False the refusal is bypassed."""

    from deltasci.llm.mock import MockLLM

    rounds_script = ['[CLAIM type=observation coverage=well-covered source=""]ok[/CLAIM]'] * 4
    llm = MockLLM(responses=rounds_script + [scripted_synthesis_response])

    config = Config(num_rounds=4, require_epistemic_humility=False, audit_enabled=False, generate_protocol=False, generate_risks=False, run_challenge=False)
    reasoner = CoReasoner(pack=biomed_pack, llm=llm, config=config)
    result = reasoner.run(idea="suspicious idea")
    # Synthesis succeeds; warnings still surface the issue
    warnings = result.hypothesis.epistemic_summary.warnings
    assert any("knowledge gaps" in w for w in warnings)
    assert any("novel syntheses" in w for w in warnings)


def test_invalid_num_rounds_raises():
    with pytest.raises(ValueError):
        Config(num_rounds=3)


def test_grounding_summary_counts(biomed_pack, scripted_llm):
    config = Config(num_rounds=4, audit_enabled=False, generate_protocol=False, generate_risks=False, run_challenge=False)
    reasoner = CoReasoner(pack=biomed_pack, llm=scripted_llm, config=config)
    result = reasoner.run(idea="Predict a thing.")
    assert len(result.grounding_summary.by_round) == 4
    for rc in result.grounding_summary.by_round:
        assert rc.claims >= 1
        assert rc.violations == 0
