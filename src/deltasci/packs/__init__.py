"""Domain pack interface and loader.

A domain pack is a directory with this layout:

    my_pack/
    ├── pack.toml      # metadata + evidence rules + scoring rubric
    └── lens.md        # the domain expert's lens (prompt fragment)

The minimal `pack.toml` looks like:

    [meta]
    name = "biomed"
    display_name = "Biomedical Sciences"
    version = "0.1.0"
    description = "Life sciences, clinical, translational research."
    example_idea = "Predict checkpoint-immunotherapy non-response in TFE3-fusion osteosarcoma ..."

    [[evidence_rules]]
    type = "published-evidence"
    source_pattern = "\\\\d{4}"  # require a 4-digit year

    [scoring_rubric]
    axes = ["data_availability", "technical_feasibility", "clinical_relevance", "novelty"]
    weights = [1.0, 1.0, 1.5, 1.0]

Built-in packs ship inside this package; user packs can live anywhere on disk
and be loaded with `load_pack("/path/to/my_pack")`.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover
    import tomli as tomllib

PACKS_ROOT = Path(__file__).parent
BUILTIN_PACK_NAMES = ("biomed", "biomed-serology", "materials", "climate")


@dataclass
class ScoringRubric:
    axes: list[str]
    weights: list[float]

    def __post_init__(self) -> None:
        if len(self.axes) != len(self.weights):
            raise ValueError(
                f"ScoringRubric axes/weights length mismatch: {len(self.axes)} vs {len(self.weights)}"
            )
        if not self.axes:
            raise ValueError("ScoringRubric must have at least one axis")


@dataclass
class DomainPack:
    """A loaded, validated domain pack."""

    name: str
    display_name: str
    version: str
    description: str
    lens: str
    evidence_rules: list[dict] = field(default_factory=list)
    scoring_rubric: ScoringRubric = field(default_factory=lambda: ScoringRubric(["overall"], [1.0]))
    example_idea: str = ""
    source_path: Path | None = None

    @classmethod
    def from_directory(cls, path: str | Path) -> "DomainPack":
        path = Path(path)
        if not path.is_dir():
            raise FileNotFoundError(f"Domain pack directory not found: {path}")

        toml_path = path / "pack.toml"
        lens_path = path / "lens.md"
        if not toml_path.is_file():
            raise FileNotFoundError(f"Missing pack.toml in {path}")
        if not lens_path.is_file():
            raise FileNotFoundError(f"Missing lens.md in {path}")

        with toml_path.open("rb") as f:
            data = tomllib.load(f)

        meta = data.get("meta", {})
        try:
            name = meta["name"]
            display_name = meta["display_name"]
            version = meta["version"]
            description = meta["description"]
        except KeyError as exc:
            raise ValueError(f"pack.toml is missing required [meta] field: {exc}") from None

        rubric_data = data.get("scoring_rubric", {})
        rubric = ScoringRubric(
            axes=list(rubric_data.get("axes", ["overall"])),
            weights=list(rubric_data.get("weights", [1.0])),
        )

        return cls(
            name=name,
            display_name=display_name,
            version=version,
            description=description,
            lens=lens_path.read_text(encoding="utf-8"),
            evidence_rules=list(data.get("evidence_rules", [])),
            scoring_rubric=rubric,
            example_idea=meta.get("example_idea", ""),
            source_path=path,
        )


def list_packs() -> list[str]:
    """List built-in pack names."""

    found: list[str] = []
    for entry in PACKS_ROOT.iterdir():
        if entry.is_dir() and (entry / "pack.toml").is_file():
            found.append(entry.name)
    return sorted(found)


def load_pack(name_or_path: str | Path) -> DomainPack:
    """Load a pack by built-in name or by filesystem path."""

    candidate = Path(name_or_path)
    if candidate.is_dir():
        return DomainPack.from_directory(candidate)

    builtin = PACKS_ROOT / str(name_or_path)
    if builtin.is_dir():
        return DomainPack.from_directory(builtin)

    available = ", ".join(list_packs()) or "(none)"
    raise FileNotFoundError(
        f"Domain pack {name_or_path!r} not found. "
        f"Built-in packs available: {available}. "
        f"Or pass a directory path to a custom pack."
    )
