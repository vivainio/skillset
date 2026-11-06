"""Tests for skillset.commands.cmd_fetch."""

from pathlib import Path

import pytest

from skillset.commands import cmd_fetch
from tests.support import Env


def test_fetch_links_nothing(
    env: Env, source_repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cmd_fetch(repo=str(source_repo))

    skills_dir = env.home / ".claude" / "skills"
    assert not skills_dir.exists() or not any(skills_dir.iterdir())
    output = capsys.readouterr().out
    assert "Fetched" in output


def test_fetch_registers_with_no_skills_enabled(env: Env, source_repo: Path) -> None:
    cmd_fetch(repo=str(source_repo))

    toml_path = env.home / ".claude" / "skillset.yaml"
    from skillset.paths import load_skillset

    data = load_skillset(toml_path)
    entry = next(iter(data["skills"].values()))
    assert entry["enabled"] == []
    assert set(entry["disabled"]) == {"skill-a", "skill-b"}
