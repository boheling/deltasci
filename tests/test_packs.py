from __future__ import annotations

import pytest

from deltasci.packs import BUILTIN_PACK_NAMES, DomainPack, list_packs, load_pack


def test_all_builtin_packs_present():
    found = set(list_packs())
    assert set(BUILTIN_PACK_NAMES).issubset(found), f"missing: {set(BUILTIN_PACK_NAMES) - found}"


@pytest.mark.parametrize("name", BUILTIN_PACK_NAMES)
def test_builtin_pack_loads(name):
    pack = load_pack(name)
    assert pack.name == name
    assert pack.display_name
    assert pack.version
    assert pack.description
    assert pack.lens.strip()
    assert pack.scoring_rubric.axes
    assert len(pack.scoring_rubric.axes) == len(pack.scoring_rubric.weights)


@pytest.mark.parametrize("name", BUILTIN_PACK_NAMES)
def test_builtin_pack_has_example_idea(name):
    pack = load_pack(name)
    assert pack.example_idea, f"pack {name} should ship with an example_idea"


def test_unknown_pack_raises():
    with pytest.raises(FileNotFoundError):
        load_pack("not-a-pack-that-exists")


def test_pack_from_directory(tmp_path):
    pack_dir = tmp_path / "mypack"
    pack_dir.mkdir()
    (pack_dir / "pack.toml").write_text(
        """
[meta]
name = "mypack"
display_name = "My Pack"
version = "0.0.1"
description = "test pack"
example_idea = "test idea"

[scoring_rubric]
axes = ["a", "b"]
weights = [1.0, 2.0]
""".strip()
    )
    (pack_dir / "lens.md").write_text("# lens\n")

    pack = DomainPack.from_directory(pack_dir)
    assert pack.name == "mypack"
    assert pack.scoring_rubric.axes == ["a", "b"]
    assert pack.scoring_rubric.weights == [1.0, 2.0]
