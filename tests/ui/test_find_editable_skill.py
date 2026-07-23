"""Tests for skillset.ui.find_skill."""

from pathlib import Path

from skillset.ui import find_skill


def test_finds_skill_in_editable_source(home_dir: Path, tmp_path: Path) -> None:
    # Create editable source with a skill
    source = tmp_path / "skills-repo"
    skill = source / "my-skill"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("# my-skill\n")

    # Set up skillset.yaml pointing to the source
    yaml_path = home_dir / ".claude" / "skillset.yaml"
    yaml_path.parent.mkdir(parents=True)
    yaml_path.write_text(f"skills:\n  my-lib:\n    editable: true\n    source: {source}\n")

    matches = find_skill("my-skill")
    assert len(matches) == 1
    found_dir, toml_key, toml_source, is_editable = matches[0]
    assert toml_key == "my-lib"
    assert is_editable is True


def test_returns_empty_when_not_found(home_dir: Path) -> None:
    yaml_path = home_dir / ".claude" / "skillset.yaml"
    yaml_path.parent.mkdir(parents=True)
    yaml_path.write_text("skills: {}\n")

    assert find_skill("nonexistent") == []


def test_returns_empty_when_no_yaml(home_dir: Path) -> None:
    assert find_skill("anything") == []


def test_skips_non_dict_entries(home_dir: Path, tmp_path: Path) -> None:
    yaml_path = home_dir / ".claude" / "skillset.yaml"
    yaml_path.parent.mkdir(parents=True)
    yaml_path.write_text("skills:\n  owner/repo:\n    enabled: ['*']\n")

    assert find_skill("some-skill") == []


def test_skips_missing_source_dir(home_dir: Path) -> None:
    yaml_path = home_dir / ".claude" / "skillset.yaml"
    yaml_path.parent.mkdir(parents=True)
    yaml_path.write_text("skills:\n  lib:\n    editable: true\n    source: /nonexistent/path\n")

    assert find_skill("skill") == []


def test_with_subpath(home_dir: Path, tmp_path: Path) -> None:
    source = tmp_path / "mono"
    skill = source / "sub" / "my-skill"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("# my-skill\n")

    yaml_path = home_dir / ".claude" / "skillset.yaml"
    yaml_path.parent.mkdir(parents=True)
    yaml_path.write_text(
        f"skills:\n  lib:\n    editable: true\n    source: {source}\n    path: sub\n"
    )

    matches = find_skill("my-skill")
    assert len(matches) == 1


def test_skips_editable_without_source(home_dir: Path) -> None:
    yaml_path = home_dir / ".claude" / "skillset.yaml"
    yaml_path.parent.mkdir(parents=True)
    yaml_path.write_text("skills:\n  lib:\n    editable: true\n")

    assert find_skill("skill") == []


def test_finds_skill_in_cached_repo(home_dir: Path) -> None:
    cache_dir = home_dir / ".cache" / "skillset" / "repos" / "owner" / "repo"
    skill = cache_dir / "zaira"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("# zaira\n")

    matches = find_skill("zaira")
    assert len(matches) == 1
    found_dir, toml_key, toml_source, is_editable = matches[0]
    assert toml_key == "owner/repo"
    assert toml_source is None
    assert is_editable is False


def test_finds_skill_in_multiple_sources(home_dir: Path, tmp_path: Path) -> None:
    # Set up editable source
    source = tmp_path / "skills-repo"
    skill = source / "zaira"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("# zaira\n")

    yaml_path = home_dir / ".claude" / "skillset.yaml"
    yaml_path.parent.mkdir(parents=True)
    yaml_path.write_text(f"skills:\n  my-lib:\n    editable: true\n    source: {source}\n")

    # Set up cached repo
    cache_dir = home_dir / ".cache" / "skillset" / "repos" / "owner" / "repo"
    skill2 = cache_dir / "zaira"
    skill2.mkdir(parents=True)
    (skill2 / "SKILL.md").write_text("# zaira\n")

    matches = find_skill("zaira")
    assert len(matches) == 2
