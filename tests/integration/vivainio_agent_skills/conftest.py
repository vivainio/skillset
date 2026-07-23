"""Shared fixtures for vivainio/agent-skills integration tests."""

from pathlib import Path

import pytest

from skillset.discovery import find_skills
from skillset.repo import get_repo_dir
from tests.support import Env

REPO = "vivainio/agent-skills"


def repo_skills(subpath: str | None = None) -> set[str]:
    """Return skill names currently discovered in the cloned integration repo."""
    source = get_repo_dir("vivainio", "agent-skills")
    if subpath:
        source /= subpath
    return {skill.name for skill in find_skills(source)}


def skills_outside(subpath: str) -> set[str]:
    """Return root-repo skills not contained in subpath."""
    source = get_repo_dir("vivainio", "agent-skills")
    excluded_root = source / subpath
    return {skill.name for skill in find_skills(source) if not skill.is_relative_to(excluded_root)}


@pytest.fixture
def env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Env:
    """Isolated environment with redirected home and project dirs."""
    home = tmp_path / "home"
    project = tmp_path / "project"
    home.mkdir()
    project.mkdir()

    monkeypatch.setattr(Path, "home", staticmethod(lambda: home))
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
