"""Shared fixtures for editable skill integration tests."""

from pathlib import Path
from unittest.mock import patch  # noqa: F401

import pytest

from skillset.commands import cmd_add, cmd_update  # noqa: F401
from skillset.paths import load_skillset, save_skillset
from tests.support import Env, LocalEnv

FIXTURES = Path(__file__).parent / "fixtures"
ALL_SKILLS = {"alpha", "beta", "gamma"}


@pytest.fixture
def env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Env:
    """Isolated environment with global scope (no local skillset.yaml)."""
    home = tmp_path / "home"
    project = tmp_path / "project"
    home.mkdir()
    project.mkdir()

    monkeypatch.setattr(Path, "home", staticmethod(lambda: home))
    monkeypatch.delenv("CLAUDE_CONFIG_DIR", raising=False)
    monkeypatch.setattr("skillset.paths.get_git_root", lambda: project)
    for mod in (
        "skillset.commands.add",
        "skillset.commands.update",
        "skillset.commands.remove",
        "skillset.commands.list",
    ):
        monkeypatch.setattr(f"{mod}.find_skillset_root", lambda: None)

    (home / ".claude").mkdir(parents=True)
    (home / ".cache" / "skillset" / "repos").mkdir(parents=True)

    return Env(home=home, project=project, tmp=tmp_path)


@pytest.fixture
def local_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> LocalEnv:
    """Isolated environment with a local skillset.yaml (project scope)."""
    home = tmp_path / "home"
    project = tmp_path / "project"
    home.mkdir()
    project.mkdir()

    monkeypatch.setattr(Path, "home", staticmethod(lambda: home))
    monkeypatch.delenv("CLAUDE_CONFIG_DIR", raising=False)
    monkeypatch.setattr("skillset.paths.get_git_root", lambda: project)
    for mod in (
        "skillset.commands.add",
        "skillset.commands.update",
        "skillset.commands.remove",
        "skillset.commands.list",
    ):
        monkeypatch.setattr(f"{mod}.find_skillset_root", lambda: project)

    (home / ".claude").mkdir(parents=True)
    (home / ".cache" / "skillset" / "repos").mkdir(parents=True)

    toml_path = project / "skillset.yaml"
    toml_path.write_text("skills: {}\n")

    return LocalEnv(
        home=home,
        project=project,
        tmp=tmp_path,
        toml_path=toml_path,
        skills_dir=project / ".claude" / "skills",
    )


def installed_skills(skills_dir: Path) -> set[str]:
    if not skills_dir.exists():
        return set()
    return {p.name for p in skills_dir.iterdir() if p.is_dir()}


def remove_skill_from_toml(toml_path: Path, skill_name: str) -> None:
    """Remove a skill name from every enabled/disabled list in skillset.yaml."""
    data = load_skillset(toml_path)
    for entry in (data.get("skills") or {}).values():
        if not isinstance(entry, dict):
            continue
        for key in ("enabled", "disabled"):
            items = entry.get(key)
            if items and skill_name in items:
                items.remove(skill_name)
    save_skillset(toml_path, data)
