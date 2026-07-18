"""Shared fixtures for command tests."""

from pathlib import Path

import pytest


@pytest.fixture
def env(tmp_path, monkeypatch):
    """Isolated environment: redirects home, git root, and mocks subprocess for git."""
    home = tmp_path / "home"
    project = tmp_path / "project"
    home.mkdir()
    project.mkdir()

    monkeypatch.setattr(Path, "home", staticmethod(lambda: home))
    monkeypatch.setattr("skillset.paths.get_git_root", lambda: project)
    # Default to global scope (no skillset.toml found) — tests can override
    for mod in (
        "skillset.commands.add",
        "skillset.commands.update",
        "skillset.commands.remove",
        "skillset.commands.list",
    ):
        monkeypatch.setattr(f"{mod}.find_skillset_root", lambda: None)

    # Create global dirs
    (home / ".claude").mkdir(parents=True)

    return type("Env", (), {"home": home, "project": project, "tmp": tmp_path})()


@pytest.fixture
def source_repo(tmp_path):
    """A fake source repo with skills and commands."""
    repo = tmp_path / "source_repo"
    for name in ("skill-a", "skill-b"):
        d = repo / name
        d.mkdir(parents=True)
        (d / "SKILL.md").write_text(f"# {name}\n")
    cmd_dir = repo / "commands"
    cmd_dir.mkdir()
    (cmd_dir / "do-thing.md").write_text("# do-thing\n")
    return repo
