"""Tests for skillset.commands.cmd_remove -- whole-repo removal (owner/repo)."""

import pytest

from skillset.commands import cmd_remove
from skillset.manifest import load_manifest, save_manifest
from skillset.paths import load_skillset, save_skillset


def _cached_repo(env, owner, name):
    repo_dir = env.home / ".cache" / "skillset" / "repos" / owner / name
    skill_dir = repo_dir / "some-skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("# some-skill\n")
    return repo_dir


def test_removes_cached_repo_dir(env, capsys):
    repo_dir = _cached_repo(env, "owner", "repo")

    cmd_remove(name="owner/repo")

    assert not repo_dir.exists()
    output = capsys.readouterr().out
    assert "Removed cached repo" in output


def test_removes_linked_skill_sourced_from_repo(env, capsys):
    repo_dir = _cached_repo(env, "owner", "repo")
    skills_dir = env.home / ".claude" / "skills"
    skills_dir.mkdir(parents=True)
    (skills_dir / "some-skill").symlink_to(repo_dir / "some-skill")

    cmd_remove(name="owner/repo")

    assert not (skills_dir / "some-skill").exists()
    output = capsys.readouterr().out
    assert "Removed skill some-skill" in output


def test_removes_skillset_yaml_entry(env, capsys):
    _cached_repo(env, "owner", "repo")
    toml_path = env.home / ".claude" / "skillset.yaml"
    save_skillset(toml_path, {"skills": {"owner/repo": {"enabled": ["*"]}}})

    cmd_remove(name="owner/repo")

    data = load_skillset(toml_path)
    assert "owner/repo" not in (data.get("skills") or {})
    output = capsys.readouterr().out
    assert "Removed owner/repo from" in output


def test_removes_manifest_entry(env):
    _cached_repo(env, "owner", "repo")
    manifest = {"owner/repo": {"scope": "global", "trial": False}}
    save_manifest(manifest)

    cmd_remove(name="owner/repo")

    assert "owner/repo" not in load_manifest()


def test_exits_when_repo_not_found(env):
    with pytest.raises(SystemExit):
        cmd_remove(name="owner/nonexistent")


def test_global_flag_removes_from_global_scope(env, capsys):
    repo_dir = _cached_repo(env, "owner", "repo")

    cmd_remove(name="owner/repo", g=True)

    assert not repo_dir.exists()
