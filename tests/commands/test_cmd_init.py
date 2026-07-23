"""Tests for skillset.commands.cmd_init."""

from pathlib import Path

import pytest

from skillset.commands import cmd_init
from tests.support import Env


def test_creates_global_skillset_yaml(env: Env) -> None:
    cmd_init(g=True)
    path = env.home / ".claude" / "skillset.yaml"
    assert path.exists()
    assert "skills:" in path.read_text()


def test_creates_local_skillset_yaml(env: Env) -> None:
    cmd_init()
    path = env.project / "skillset.yaml"
    assert path.exists()
    assert "skills:" in path.read_text()


def test_exits_if_already_exists(env: Env) -> None:
    path = env.home / ".claude" / "skillset.yaml"
    path.write_text("skills: {}\n")

    with pytest.raises(SystemExit):
        cmd_init(g=True)


def test_local_outside_git_creates_in_cwd(
    env: Env, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr("skillset.paths.get_git_root", lambda: None)
    monkeypatch.chdir(tmp_path)
    cmd_init()
    assert (tmp_path / "skillset.yaml").exists()
