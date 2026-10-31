"""Tests for skillset.commands.cmd_get."""

from pathlib import Path

import pytest

from skillset.commands import cmd_get
from skillset.paths import abbrev
from tests.support import Env


def _cache_skill(env: Env, owner: str, repo: str, name: str, description: str = "A skill") -> Path:
    skill_dir = env.home / ".cache" / "skillset" / "repos" / owner / repo / name
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: {description}\n---\n# {name} body\n"
    )
    return skill_dir


def test_get_prints_skill_md_and_resources(env: Env, capsys: pytest.CaptureFixture[str]) -> None:
    skill_dir = _cache_skill(env, "owner", "repo", "zaira", "Access Jira")
    (skill_dir / "scripts").mkdir()
    (skill_dir / "scripts" / "run.sh").write_text("echo hi")
    (skill_dir / ".hidden").write_text("x")

    cmd_get(query=["zaira"])

    out = capsys.readouterr().out
    assert "# zaira body" in out
    assert "owner/repo" in out
    assert abbrev(skill_dir.resolve()) in out
    assert abbrev(skill_dir.resolve()).startswith("~")
    assert abbrev((skill_dir / "scripts" / "run.sh").resolve()) in out
    assert ".hidden" not in out


def test_get_does_not_install(env: Env) -> None:
    _cache_skill(env, "owner", "repo", "zaira")

    cmd_get(query=["zaira"])

    assert not (env.home / ".claude" / "skills" / "zaira").exists()


def test_get_no_resources_section_when_only_skill_md(
    env: Env, capsys: pytest.CaptureFixture[str]
) -> None:
    _cache_skill(env, "owner", "repo", "zaira")

    cmd_get(query=["zaira"])

    assert "# Resources" not in capsys.readouterr().out


def test_get_no_match_exits(env: Env, capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        cmd_get(query=["nothing"])
    assert exc.value.code == 1
    assert "No matching skills found" in capsys.readouterr().err


def test_get_ambiguous_lists_candidates(env: Env, capsys: pytest.CaptureFixture[str]) -> None:
    _cache_skill(env, "owner", "repo", "jira-a", "Jira thing")
    _cache_skill(env, "owner", "repo", "jira-b", "Jira other")

    with pytest.raises(SystemExit) as exc:
        cmd_get(query=["jira"])

    assert exc.value.code == 1
    err = capsys.readouterr().err
    assert "jira-a" in err
    assert "jira-b" in err


def test_get_exact_name_beats_partial(env: Env, capsys: pytest.CaptureFixture[str]) -> None:
    _cache_skill(env, "owner", "repo", "jira", "Jira basics")
    _cache_skill(env, "owner", "repo", "jira-extra", "More Jira")

    cmd_get(query=["jira"])

    assert "# jira body" in capsys.readouterr().out
