"""Tests for skillset.commands.cmd_get."""

from pathlib import Path

import pytest

from skillset.commands import cmd_get
from skillset.manifest import load_manifest
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
    assert "follow the instructions below" in out
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


def test_get_with_repo_scopes_to_that_repo(env: Env, capsys: pytest.CaptureFixture[str]) -> None:
    _cache_skill(env, "owner", "repo", "zaira")
    _cache_skill(env, "other", "repo", "zaira", "Other zaira")

    cmd_get(query=["other/repo", "zaira"])

    out = capsys.readouterr().out
    assert "[other/repo]" in out
    assert "owner/repo" not in out


def test_get_with_repo_clones_when_not_cached(
    env: Env, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_clone(owner: str, repo: str, ref: str | None = None) -> Path:
        return _cache_skill(env, owner, repo, "zaira").parent

    monkeypatch.setattr("skillset.commands.get.clone_or_pull", fake_clone)

    cmd_get(query=["new/repo", "zaira"])

    captured = capsys.readouterr()
    assert "[new/repo]" in captured.out
    assert "trial repo" in captured.err
    assert load_manifest()["new/repo"]["trial"] is True


def test_get_with_repo_uses_cache_without_pulling(
    env: Env, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _cache_skill(env, "owner", "repo", "zaira")

    def boom(*_a: object, **_k: object) -> Path:
        raise AssertionError("must not hit the network for a cached repo")

    monkeypatch.setattr("skillset.commands.get.clone_or_pull", boom)

    cmd_get(query=["owner/repo", "zaira"])

    assert "# zaira body" in capsys.readouterr().out
    assert "owner/repo" not in load_manifest()


def test_get_with_repo_clone_failure_exits(
    env: Env, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail(*_a: object, **_k: object) -> Path:
        raise RuntimeError("no network")

    monkeypatch.setattr("skillset.commands.get.clone_or_pull", fail)

    with pytest.raises(SystemExit) as exc:
        cmd_get(query=["new/repo", "zaira"])
    assert exc.value.code == 1
    assert "Could not fetch new/repo" in capsys.readouterr().err
