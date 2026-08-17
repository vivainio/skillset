"""Shared test fixtures."""

from pathlib import Path

import pytest


@pytest.fixture
def home_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect Path.home() to a temp directory."""
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))
    monkeypatch.delenv("CLAUDE_CONFIG_DIR", raising=False)
    return tmp_path


@pytest.fixture
def git_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Fake git repo root — patches get_git_root to return tmp_path."""
    monkeypatch.setattr("skillset.paths.get_git_root", lambda: tmp_path)
    return tmp_path


@pytest.fixture
def skill_repo(tmp_path: Path) -> Path:
    """Create a fake repo with skill-a, skill-b, and a command."""
    repo = tmp_path / "repo"
    for name in ("skill-a", "skill-b"):
        skill_dir = repo / name
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(f"# {name}\n")

    # A dot-dir skill that should be ignored
    hidden = repo / ".hidden" / "secret-skill"
    hidden.mkdir(parents=True)
    (hidden / "SKILL.md").write_text("# secret\n")

    # A command
    cmd_dir = repo / "commands"
    cmd_dir.mkdir()
    (cmd_dir / "do-thing.md").write_text("# do-thing\n")

    return repo
