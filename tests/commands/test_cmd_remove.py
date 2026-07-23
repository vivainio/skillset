"""Tests for skillset.commands.cmd_remove."""

from pathlib import Path

import pytest

from skillset.commands import cmd_remove
from skillset.linking import copy_dir
from skillset.paths import load_skillset
from tests.support import Env


def test_removes_symlinked_skill(
    env: Env, source_repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    skills_dir = env.home / ".claude" / "skills"
    skills_dir.mkdir(parents=True)
    (skills_dir / "skill-a").symlink_to(source_repo / "skill-a")

    cmd_remove(name="skill-a")
    assert not (skills_dir / "skill-a").exists()
    output = capsys.readouterr().out
    assert "Removed" in output


def test_removes_copied_skill(
    env: Env, source_repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    skills_dir = env.home / ".claude" / "skills"
    skills_dir.mkdir(parents=True)
    copy_dir(source_repo / "skill-a", skills_dir / "skill-a")

    cmd_remove(name="skill-a")
    assert not (skills_dir / "skill-a").exists()


def test_remove_persists_disabled_and_removes_literal_enabled(env: Env, source_repo: Path) -> None:
    skills_dir = env.home / ".claude" / "skills"
    skills_dir.mkdir(parents=True)
    (skills_dir / "skill-a").symlink_to(source_repo / "skill-a")
    config_path = env.home / ".claude" / "skillset.yaml"
    config_path.write_text(
        f"skills:\n  owner/repo:\n    editable: true\n"
        f"    source: {source_repo}\n    enabled: [skill-a, skill-b]\n"
    )

    cmd_remove(name="skill-a")

    entry = load_skillset(config_path)["skills"]["owner/repo"]
    assert list(entry["enabled"]) == ["skill-b"]
    assert list(entry["disabled"]) == ["skill-a"]


def test_exits_when_skill_not_found(env: Env) -> None:
    with pytest.raises(SystemExit):
        cmd_remove(name="nonexistent")


def test_exits_for_unmanaged_skill(env: Env) -> None:
    skills_dir = env.home / ".claude" / "skills"
    skills_dir.mkdir(parents=True)
    manual = skills_dir / "manual"
    manual.mkdir()
    (manual / "SKILL.md").write_text("x")

    with pytest.raises(SystemExit):
        cmd_remove(name="manual")


def test_no_name_exits(env: Env) -> None:
    with pytest.raises(SystemExit):
        cmd_remove()


def test_global_flag_uses_global_dir(
    env: Env, source_repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """With --global, removes from global dir even when skillset.toml exists."""
    skills_dir = env.home / ".claude" / "skills"
    skills_dir.mkdir(parents=True)
    (skills_dir / "skill-a").symlink_to(source_repo / "skill-a")

    cmd_remove(name="skill-a", g=True)
    assert not (skills_dir / "skill-a").exists()


def test_glob_pattern(env: Env, source_repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    skills_dir = env.home / ".claude" / "skills"
    skills_dir.mkdir(parents=True)
    (skills_dir / "skill-a").symlink_to(source_repo / "skill-a")
    (skills_dir / "skill-b").symlink_to(source_repo / "skill-b")

    cmd_remove(name="skill-*")
    assert not (skills_dir / "skill-a").exists()
    assert not (skills_dir / "skill-b").exists()


def test_percent_wildcard_alias(
    env: Env, source_repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`%` is a shell-safe alias for `*` so patterns need no quoting."""
    skills_dir = env.home / ".claude" / "skills"
    skills_dir.mkdir(parents=True)
    (skills_dir / "skill-a").symlink_to(source_repo / "skill-a")
    (skills_dir / "skill-b").symlink_to(source_repo / "skill-b")

    cmd_remove(name="skill-%")
    assert not (skills_dir / "skill-a").exists()
    assert not (skills_dir / "skill-b").exists()


def test_glob_no_match_exits(env: Env, source_repo: Path) -> None:
    skills_dir = env.home / ".claude" / "skills"
    skills_dir.mkdir(parents=True)
    (skills_dir / "skill-a").symlink_to(source_repo / "skill-a")

    with pytest.raises(SystemExit):
        cmd_remove(name="zzz-*")


def test_glob_no_skills_dir_exits(env: Env) -> None:
    with pytest.raises(SystemExit):
        cmd_remove(name="skill-*")


def test_remove_local_scope(
    env: Env, source_repo: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """When skillset_root is found, remove from project skills dir."""
    monkeypatch.setattr("skillset.commands.remove.find_skillset_root", lambda: env.project)
    project_skills = env.project / ".claude" / "skills"
    project_skills.mkdir(parents=True)
    (project_skills / "skill-a").symlink_to(source_repo / "skill-a")

    cmd_remove(name="skill-a")
    assert not (project_skills / "skill-a").exists()
    output = capsys.readouterr().out
    assert "Removed" in output
