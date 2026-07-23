"""Tests for skillset.paths.add_to_global_skillset."""

from pathlib import Path

from skillset.paths import add_to_global_skillset, load_skillset


def test_creates_entry(home_dir: Path) -> None:
    toml_path = home_dir / ".claude" / "skillset.yaml"
    toml_path.parent.mkdir(parents=True)
    toml_path.write_text("skills: {}\n")

    result = add_to_global_skillset("owner/repo", enabled=["*"])
    assert result is True

    data = load_skillset(toml_path)
    assert "owner/repo" in data["skills"]
    assert list(data["skills"]["owner/repo"]["enabled"]) == ["*"]


def test_no_duplicate(home_dir: Path) -> None:
    toml_path = home_dir / ".claude" / "skillset.yaml"
    toml_path.parent.mkdir(parents=True)
    toml_path.write_text("skills:\n  owner/repo:\n    enabled: ['*']\n")

    result = add_to_global_skillset("owner/repo", enabled=["*"])
    assert result is False


def test_no_file(home_dir: Path) -> None:
    result = add_to_global_skillset("owner/repo", enabled=["*"])
    assert result is False


def test_with_skills(home_dir: Path) -> None:
    toml_path = home_dir / ".claude" / "skillset.yaml"
    toml_path.parent.mkdir(parents=True)
    toml_path.write_text("skills: {}\n")

    result = add_to_global_skillset("owner/repo", enabled=["skill-a"], disabled=["skill-b"])
    assert result is True

    data = load_skillset(toml_path)
    entry = data["skills"]["owner/repo"]
    assert list(entry["enabled"]) == ["skill-a"]
    assert list(entry["disabled"]) == ["skill-b"]


def test_editable(home_dir: Path) -> None:
    toml_path = home_dir / ".claude" / "skillset.yaml"
    toml_path.parent.mkdir(parents=True)
    toml_path.write_text("skills: {}\n")

    result = add_to_global_skillset(
        "my-skills", editable=True, source="~/local/skills", enabled=["*"]
    )
    assert result is True

    data = load_skillset(toml_path)
    entry = data["skills"]["my-skills"]
    assert entry["editable"] is True
    assert entry["source"] == "~/local/skills"


def test_snapshot_with_ref(home_dir: Path) -> None:
    toml_path = home_dir / ".claude" / "skillset.yaml"
    toml_path.parent.mkdir(parents=True)
    toml_path.write_text("skills: {}\n")

    from skillset.paths import add_to_skillset

    result = add_to_skillset(
        toml_path,
        "owner/repo",
        enabled=["*"],
        ref="abc1234",
        snapshot=True,
    )
    assert result is True

    data = load_skillset(toml_path)
    entry = data["skills"]["owner/repo"]
    assert entry["snapshot"] is True
    assert entry["ref"] == "abc1234"
