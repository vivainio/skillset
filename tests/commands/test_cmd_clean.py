"""Tests for skillset.commands.cmd_clean."""

from pathlib import Path

import pytest

from skillset.commands import cmd_clean
from skillset.linking import copy_dir
from skillset.manifest import load_manifest, record_install
from tests.support import Env


def test_no_trial_skills(env: Env, capsys: pytest.CaptureFixture[str]) -> None:
    cmd_clean()
    output = capsys.readouterr().out
    assert "No trial skills to clean" in output


def test_cleans_trial_copies(
    env: Env, source_repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    skills_dir = env.home / ".claude" / "skills"
    skills_dir.mkdir(parents=True)
    copy_dir(source_repo / "skill-a", skills_dir / "skill-a", source_label="test/repo")

    record_install("test/repo", trial=True)

    cmd_clean()
    assert not (skills_dir / "skill-a").exists()
    output = capsys.readouterr().out
    assert "Removed" in output
    assert "Cleaned" in output


def test_cleans_trial_symlinks(
    env: Env, source_repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    skills_dir = env.home / ".claude" / "skills"
    skills_dir.mkdir(parents=True)
    (skills_dir / "skill-a").symlink_to(source_repo / "skill-a")

    repo_key = str(source_repo)
    record_install(repo_key, trial=True)

    cmd_clean()
    assert not (skills_dir / "skill-a").exists()


def test_cleans_cached_repo(env: Env, capsys: pytest.CaptureFixture[str]) -> None:
    repo_key = "owner/repo"
    cache_dir = env.home / ".cache" / "skillset" / "repos" / "owner" / "repo"
    cache_dir.mkdir(parents=True)
    (cache_dir / "dummy").write_text("x")

    skills_dir = env.home / ".claude" / "skills"
    skills_dir.mkdir(parents=True)
    copy_dir(cache_dir, skills_dir / "skill-a", source_label=repo_key)

    record_install(repo_key, trial=True)

    cmd_clean()
    assert not cache_dir.exists()
    output = capsys.readouterr().out
    assert "Removed cached repo" in output

    manifest = load_manifest()
    assert repo_key not in manifest


def test_cleans_linked_cached_repo(
    env: Env, source_repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo_key = "owner/repo"
    cache_owner = env.home / ".cache" / "skillset" / "repos" / "owner"
    cache_owner.mkdir(parents=True)
    (cache_owner / "repo").symlink_to(source_repo)

    skills_dir = env.home / ".claude" / "skills"
    skills_dir.mkdir(parents=True)
    copy_dir(source_repo / "skill-a", skills_dir / "skill-a", source_label=repo_key)

    record_install(repo_key, trial=True)

    cmd_clean()
    assert not (cache_owner / "repo").exists()


def test_local_scope_outside_git_skips(
    env: Env, source_repo: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("skillset.paths.get_git_root", lambda: None)
    monkeypatch.setattr("skillset.commands.remove.get_project_skills_dir", lambda: None)

    record_install("test/repo", trial=True, scope="local")

    cmd_clean()
    output = capsys.readouterr().out
    assert "Skipping" in output


def test_cleans_with_unmanaged_item(
    env: Env, source_repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Unmanaged items in skills dir are skipped during clean."""
    skills_dir = env.home / ".claude" / "skills"
    skills_dir.mkdir(parents=True)
    # One managed trial skill
    copy_dir(source_repo / "skill-a", skills_dir / "skill-a", source_label="test/repo")
    # One unmanaged (manual) skill
    manual = skills_dir / "manual-skill"
    manual.mkdir()
    (manual / "SKILL.md").write_text("# manual\n")

    record_install("test/repo", trial=True)

    cmd_clean()
    assert not (skills_dir / "skill-a").exists()
    assert (skills_dir / "manual-skill").exists()
