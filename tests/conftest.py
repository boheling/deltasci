from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


@pytest.fixture
def biomed_pack():
    from deltasci.packs import load_pack

    return load_pack("biomed")


@pytest.fixture
def materials_pack():
    from deltasci.packs import load_pack

    return load_pack("materials")


@pytest.fixture
def climate_pack():
    from deltasci.packs import load_pack

    return load_pack("climate")


@pytest.fixture
def scripted_round_responses():
    """A 4-round script with valid CLAIM tags (with coverage), at least one
    KNOWLEDGE_GAP, and at least one NOVEL_SYNTHESIS so the epistemic-humility
    gate passes.
    """

    return [
        # domain_r1
        """
The proposed system targets a well-characterized clinical population.

[CLAIM type=published-evidence coverage=well-covered source="Smith et al 2022, Nature 600:123"]The mechanism has prior evidence.[/CLAIM]
[CLAIM type=observation coverage=sparse source=""]The unmet need is well-recognized in the clinic.[/CLAIM]
[KNOWLEDGE_GAP category=lab-tribal-knowledge]Are there site-specific cohort biases not in the public dataset?[/KNOWLEDGE_GAP]
        """.strip(),
        # engineer_r1
        """
A graph-based representation is appropriate.

[CLAIM type=engineering-precedent coverage=well-covered source="github.com/example/repo-2024"]A reference implementation exists.[/CLAIM]
[CLAIM type=observation coverage=sparse source=""]Compute requirements are modest given available infrastructure.[/CLAIM]
[NOVEL_SYNTHESIS rationale="combines two known facts in a new way"]Combining the proposed graph backbone with the domain-specific edge schema has not been written up explicitly.[/NOVEL_SYNTHESIS]
        """.strip(),
        # domain_r2
        """
The proposed metrics need refinement.

[CLAIM type=published-evidence coverage=well-covered source="Jones et al 2023, JAMA 329:456"]Clinically meaningful thresholds for this task have been established.[/CLAIM]
[CLAIM type=observation coverage=sparse source=""]A falsifiable threshold of >5 percentage points improvement over standard of care is realistic.[/CLAIM]
        """.strip(),
        # engineer_r2
        """
The integrated plan combines mechanism with method.

[CLAIM type=engineering-precedent coverage=well-covered source="github.com/example/baseline-2024"]Strong baselines are available.[/CLAIM]
[CLAIM type=observation coverage=sparse source=""]Expected AUC improvement is 0.05 over baseline.[/CLAIM]
        """.strip(),
    ]


@pytest.fixture
def scripted_synthesis_response():
    return json.dumps(
        {
            "title": "Mock graph-based predictor",
            "statement": "A graph neural network leveraging the domain mechanism is expected to outperform tabular baselines on the held-out cohort.",
            "domain_grounding": {
                "mechanism": "The mechanism is well-characterized in the literature.",
                "unmet_need": "Standard of care does not capture relational structure.",
                "expected_impact": "Clinically meaningful improvement on outcome prediction.",
            },
            "technical_approach": {
                "core_method": "Graph neural network with domain-specific edges.",
                "key_innovation": "Domain-derived edge weighting.",
                "implementation_path": "Public dataset -> baseline GNN -> domain edges -> external validation.",
            },
            "falsifiability": {
                "prediction": "Held-out external AUC >= 0.85",
                "threshold": "AUC >= 0.85 with 95% CI lower bound > 0.80",
                "null_outcome": "AUC <= baseline + 0.01 falsifies the hypothesis.",
            },
            "feasibility_scores": {
                "data_availability": 4,
                "technical_feasibility": 4,
                "clinical_relevance": 5,
                "novelty": 3,
                "ethical_clearability": 4,
            },
            "feasibility_justifications": {
                "data_availability": "Public dataset available.",
                "technical_feasibility": "Standard architecture.",
                "clinical_relevance": "Direct alignment with workflow.",
                "novelty": "Incremental but well-motivated.",
                "ethical_clearability": "Existing IRB-cleared cohort.",
            },
        }
    )


@pytest.fixture
def scripted_llm(scripted_round_responses, scripted_synthesis_response):
    from deltasci.llm.mock import MockLLM

    return MockLLM(responses=list(scripted_round_responses) + [scripted_synthesis_response])
