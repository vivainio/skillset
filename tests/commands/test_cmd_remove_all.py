"""Tests for skillset.commands.cmd_remove_all -- removing every registered repo."""

from pathlib import Path

import pytest

from skillset.commands import cmd_remove_all
from skillset.manifest import load_manifest, save_manifest
from skillset.paths import get_cache_dir, load_skillset, save_skillset
from tests.support import Env


def _cached_repo(env: Env, owner: str, name: str) -> Path:
    repo_dir = env.home / ".cache" / "skillset" / "repos" / owner / name
    skill_dir = repo_dir / "some-skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("# some-skill\n")
    return repo_dir


def test_removes_every_registered_repo(env: Env, capsys: pytest.CaptureFixture[str]) -> None:
    repo_a = _cached_repo(env, "owner", "repo-a")
    repo_b = _cached_repo(env, "owner", "repo-b")
    skills_dir = env.home / ".claude" / "skills"
    skills_dir.mkdir(parents=True)
    (skills_dir / "skill-a").symlink_to(repo_a / "some-skill")
    (skills_dir / "skill-b").symlink_to(repo_b / "some-skill")
    toml_path = env.home / ".claude" / "skillset.yaml"
    save_skillset(
        toml_path,
        {
            "skills": {
                "owner/repo-a": {"enabled": ["*"]},
                "owner/repo-b": {"enabled": ["*"]},
            }
        },
    )

    cmd_remove_all()

    assert not (skills_dir / "skill-a").exists()
    assert not (skills_dir / "skill-b").exists()
    assert not repo_a.exists()
    assert not repo_b.exists()
    data = load_skillset(toml_path)
    assert data.get("skills") == {}


def test_no_registered_repos_prints_message(env: Env, capsys: pytest.CaptureFixture[str]) -> None:
    cmd_remove_all()

    output = capsys.readouterr().out
    assert "No repos registered" in output


def test_wipes_untracked_and_trial_repos_from_cache(
    env: Env, capsys: pytest.CaptureFixture[str]
) -> None:
    repo_a = _cached_repo(env, "owner", "repo-a")
    orphan = get_cache_dir() / "owner" / "orphan-repo"
    orphan.mkdir(parents=True)
    toml_path = env.home / ".claude" / "skillset.yaml"
    save_skillset(toml_path, {"skills": {"owner/repo-a": {"enabled": ["*"]}}})
    save_manifest({"owner/repo-a": {"scope": "global", "trial": False}})

    cmd_remove_all()

    assert not repo_a.exists()
    assert not orphan.exists()
    assert not get_cache_dir().exists()
    assert load_manifest() == {}
    output = capsys.readouterr().out
    assert "Removed cache dir" in output


def test_global_flag_removes_from_global_scope(
    env: Env, capsys: pytest.CaptureFixture[str]
) -> None:
    repo_dir = _cached_repo(env, "owner", "repo")
    toml_path = env.home / ".claude" / "skillset.yaml"
    save_skillset(toml_path, {"skills": {"owner/repo": {"enabled": ["*"]}}})

    cmd_remove_all(g=True)

    assert not repo_dir.exists()
    data = load_skillset(toml_path)
    assert data.get("skills") == {}
