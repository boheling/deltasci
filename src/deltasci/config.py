from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

GroundingStrictness = Literal["high", "medium", "low"]


@dataclass
class Config:
    """Runtime configuration for a CoReasoner session.

    Values are resolved with this precedence:
    explicit kwargs > environment variables > defaults.
    """

    llm_provider: str = field(default_factory=lambda: os.environ.get("DELTASCI_LLM_PROVIDER", "auto"))
    model: str | None = field(default_factory=lambda: os.environ.get("DELTASCI_MODEL"))
    num_rounds: int = 4
    grounding_strictness: GroundingStrictness = "high"
    require_falsifiability: bool = True
    require_epistemic_humility: bool = True
    audit_enabled: bool = True
    audit_cache_path: Path | None = None
    audit_timeout_seconds: float = 10.0
    generate_protocol: bool = True
    generate_risks: bool = True
    run_challenge: bool = True
    generate_notebook: bool = True
    auto_view: bool = True
    interactive: bool = False
    output_dir: Path = field(default_factory=lambda: Path(os.environ.get("DELTASCI_OUTPUT_DIR", "deltasci-output")))
    max_repair_attempts: int = 1

    def __post_init__(self) -> None:
        if self.num_rounds < 2 or self.num_rounds % 2 != 0:
            raise ValueError(
                f"num_rounds must be an even integer >= 2 (got {self.num_rounds}). "
                f"Each role must take an equal number of turns."
            )
        if self.grounding_strictness not in ("high", "medium", "low"):
            raise ValueError(f"grounding_strictness must be high|medium|low, got {self.grounding_strictness!r}")
        self.output_dir = Path(self.output_dir)
