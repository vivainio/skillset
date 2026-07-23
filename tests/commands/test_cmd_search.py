"""Tests for skillset.commands.cmd_search."""

from pathlib import Path

import pytest

from skillset.commands import cmd_search
from skillset.paths import save_skillset
from tests.support import Env


def _cache_repo(env: Env, owner: str, name: str, skills: dict[str, str]) -> Path:
    """Create a fake cached repo with the given skill_name -> description map."""
    repo_dir = env.home / ".cache" / "skillset" / "repos" / owner / name
    for skill_name, description in skills.items():
        skill_dir = repo_dir / skill_name
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            f"---\nname: {skill_name}\ndescription: {description}\n---\n# {skill_name}\n"
        )
    return repo_dir


def test_search_no_sources(env: Env, capsys: pytest.CaptureFixture[str]) -> None:
    cmd_search(query=["jira"])
    output = capsys.readouterr().out
    assert "No matching skills found" in output


def test_search_matches_description(env: Env, capsys: pytest.CaptureFixture[str]) -> None:
    _cache_repo(env, "owner", "repo", {"zaira": "Access Jira tickets offline"})

    cmd_search(query=["jira"])
    output = capsys.readouterr().out
    assert "owner/repo" in output
    assert "zaira" in output
    assert "1 skill(s) found" in output


def test_search_matches_name(env: Env, capsys: pytest.CaptureFixture[str]) -> None:
    _cache_repo(env, "owner", "repo", {"jira-check": "Pre-release checklist"})

    cmd_search(query=["jira"])
    output = capsys.readouterr().out
    assert "jira-check" in output


def test_search_requires_all_terms(env: Env, capsys: pytest.CaptureFixture[str]) -> None:
    _cache_repo(env, "owner", "repo", {"zaira": "Access Jira tickets offline"})

    cmd_search(query=["jira", "nomatch"])
    output = capsys.readouterr().out
    assert "No matching skills found" in output


def test_search_glob_prefix(env: Env, capsys: pytest.CaptureFixture[str]) -> None:
    _cache_repo(
        env,
        "owner",
        "repo",
        {"jira-check": "Pre-release checklist", "zaira": "Access Jira tickets offline"},
    )

    cmd_search(query=["jira-*"])
    output = capsys.readouterr().out
    assert "jira-check" in output
    assert "zaira" not in output


def test_search_glob_percent_alias(env: Env, capsys: pytest.CaptureFixture[str]) -> None:
    _cache_repo(env, "owner", "repo", {"jira-check": "Pre-release checklist"})

    cmd_search(query=["jira-%"])
    output = capsys.readouterr().out
    assert "jira-check" in output


def test_search_glob_substring(env: Env, capsys: pytest.CaptureFixture[str]) -> None:
    _cache_repo(
        env,
        "owner",
        "repo",
        {"zaira": "Access Jira tickets offline", "other": "Unrelated"},
    )

    cmd_search(query=["%jira%"])
    output = capsys.readouterr().out
    assert "zaira" in output
    assert "other" not in output


def test_search_skips_local_alias_dir(env: Env, capsys: pytest.CaptureFixture[str]) -> None:
    """The repos/local/ dir is for editable-source symlinks -- not scanned directly."""
    _cache_repo(env, "local", "some-repo", {"zaira": "Access Jira tickets offline"})

    cmd_search(query=["jira"])
    output = capsys.readouterr().out
    assert "No matching skills found" in output


def test_search_editable_source(
    env: Env, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    editable_repo = tmp_path / "editable_repo"
    skill_dir = editable_repo / "zaira"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: zaira\ndescription: Access Jira tickets offline\n---\n# zaira\n"
    )

    toml_path = env.home / ".claude" / "skillset.yaml"
    save_skillset(
        toml_path,
        {
            "skills": {
                "my/editable": {
                    "editable": True,
                    "source": str(editable_repo),
                    "enabled": ["*"],
                }
            }
        },
    )

    cmd_search(query=["jira"])
    output = capsys.readouterr().out
    assert "my/editable" in output
    assert "zaira" in output


def test_search_installed_unmanaged_skill(env: Env, capsys: pytest.CaptureFixture[str]) -> None:
    skill_dir = env.home / ".claude" / "skills" / "personal"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: personal\ndescription: Personal Jira workflow\n---\n"
    )

    cmd_search(query=["jira"])

    output = capsys.readouterr().out
    assert "Unmanaged:" in output
    assert "personal" in output


def test_search_saved_unmanaged_skill(env: Env, capsys: pytest.CaptureFixture[str]) -> None:
    skill_dir = env.home / ".claude" / ".skillset" / "skills" / "personal"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: personal\ndescription: Personal Jira workflow\n---\n"
    )

    cmd_search(query=["jira"])

    output = capsys.readouterr().out
    assert "Saved unmanaged:" in output
    assert "personal" in output
