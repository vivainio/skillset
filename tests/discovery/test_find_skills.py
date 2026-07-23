"""Tests for skillset.discovery.find_skills."""

from pathlib import Path

from skillset.discovery import find_skills


def test_finds_skill_directories(skill_repo: Path) -> None:
    skills = find_skills(skill_repo)
    names = sorted(s.name for s in skills)
    assert names == ["skill-a", "skill-b"]


def test_excludes_hidden_directories(skill_repo: Path) -> None:
    skills = find_skills(skill_repo)
    names = [s.name for s in skills]
    assert "secret-skill" not in names


def test_finds_nested_skills(tmp_path: Path) -> None:
    nested = tmp_path / "group" / "my-skill"
    nested.mkdir(parents=True)
    (nested / "SKILL.md").write_text("# nested\n")

    skills = find_skills(tmp_path)
    assert len(skills) == 1
    assert skills[0].name == "my-skill"


def test_returns_empty_for_no_skills(tmp_path: Path) -> None:
    assert find_skills(tmp_path) == []
