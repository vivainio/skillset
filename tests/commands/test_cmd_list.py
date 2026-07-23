"""Tests for skillset.commands.cmd_list."""

from pathlib import Path

import pytest

from skillset.commands import cmd_list
from skillset.linking import copy_dir
from tests.support import Env


def test_no_skills_installed(env: Env, capsys: pytest.CaptureFixture[str]) -> None:
    cmd_list()
    output = capsys.readouterr().out
    assert "No skills, commands, or repos found" in output


def test_lists_global_skills(
    env: Env, source_repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    skills_dir = env.home / ".claude" / "skills"
    skills_dir.mkdir(parents=True)
    copy_dir(source_repo / "skill-a", skills_dir / "skill-a", source_label="test/repo")

    cmd_list()
    output = capsys.readouterr().out
    assert "Global skills" in output
    assert "skill-a" in output


def test_lists_skill_description_size(
    env: Env, source_repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    skill = source_repo / "skill-a"
    description = "Useful test skill"
    (skill / "SKILL.md").write_text(
        f"---\nname: skill-a\ndescription: {description}\n---\n# Skill\n"
    )
    skills_dir = env.home / ".claude" / "skills"
    skills_dir.mkdir(parents=True)
    (skills_dir / "skill-a").symlink_to(skill)

    cmd_list()

    output = capsys.readouterr().out
    assert f"skill-a  ({len(description)} chars)" in output


def test_lists_zero_size_for_skill_without_description(
    env: Env, source_repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    skills_dir = env.home / ".claude" / "skills"
    skills_dir.mkdir(parents=True)
    (skills_dir / "skill-a").symlink_to(source_repo / "skill-a")

    cmd_list()

    output = capsys.readouterr().out
    assert "skill-a  (0 chars)" in output


def test_aligns_skill_description_sizes(
    env: Env, source_repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    skills_dir = env.home / ".claude" / "skills"
    skills_dir.mkdir(parents=True)
    (skills_dir / "a").symlink_to(source_repo / "skill-a")
    (skills_dir / "long-name").symlink_to(source_repo / "skill-b")

    cmd_list()

    lines = capsys.readouterr().out.splitlines()
    skill_lines = [line for line in lines if "(0 chars)" in line]
    assert [line.index("(") for line in skill_lines] == [len("    long-name  ")] * 2


def test_lists_symlinked_skills(
    env: Env, source_repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    skills_dir = env.home / ".claude" / "skills"
    skills_dir.mkdir(parents=True)
    (skills_dir / "skill-a").symlink_to(source_repo / "skill-a")

    cmd_list()
    output = capsys.readouterr().out
    assert "skill-a" in output


def test_broken_link_displayed(env: Env, capsys: pytest.CaptureFixture[str]) -> None:
    skills_dir = env.home / ".claude" / "skills"
    skills_dir.mkdir(parents=True)
    broken = skills_dir / "broken-skill"
    broken.symlink_to("/nonexistent/path")

    cmd_list()
    output = capsys.readouterr().out
    assert "broken link" in output


def test_prune_removes_broken_links(env: Env, capsys: pytest.CaptureFixture[str]) -> None:
    skills_dir = env.home / ".claude" / "skills"
    skills_dir.mkdir(parents=True)
    broken = skills_dir / "broken-skill"
    broken.symlink_to("/nonexistent/path")

    cmd_list(prune=True)
    output = capsys.readouterr().out
    assert "pruned broken link" in output
    assert not broken.exists()


def test_lists_repos(env: Env, capsys: pytest.CaptureFixture[str]) -> None:
    cache_dir = env.home / ".cache" / "skillset" / "repos" / "owner" / "repo"
    cache_dir.mkdir(parents=True)

    cmd_list()
    output = capsys.readouterr().out
    assert "Repos" in output
    assert "owner/repo" in output


def test_lists_linked_repo(env: Env, source_repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    cache_dir = env.home / ".cache" / "skillset" / "repos" / "owner"
    cache_dir.mkdir(parents=True)
    (cache_dir / "repo").symlink_to(source_repo)

    cmd_list()
    output = capsys.readouterr().out
    assert "owner/repo" in output
    assert "->" in output


def test_manual_skill(env: Env, capsys: pytest.CaptureFixture[str]) -> None:
    skills_dir = env.home / ".claude" / "skills"
    skills_dir.mkdir(parents=True)
    manual = skills_dir / "manual-skill"
    manual.mkdir()
    (manual / "SKILL.md").write_text("# manual\n")

    cmd_list()
    output = capsys.readouterr().out
    assert "Unmanaged:" in output


def test_profile_stored_skill_is_listed_as_unmanaged(
    env: Env, capsys: pytest.CaptureFixture[str]
) -> None:
    skills_dir = env.home / ".claude" / "skills"
    stored = env.home / ".claude" / ".skillset" / "skills" / "personal"
    stored.mkdir(parents=True)
    (stored / "SKILL.md").write_text("# personal\n")
    skills_dir.mkdir(parents=True)
    (skills_dir / "personal").symlink_to(stored)

    cmd_list()

    output = capsys.readouterr().out
    assert "Unmanaged:" in output
    assert "personal" in output
    assert ".skillset/skills" not in output


def test_trial_skill_tagged(
    env: Env, source_repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    from skillset.manifest import record_install

    skills_dir = env.home / ".claude" / "skills"
    skills_dir.mkdir(parents=True)
    copy_dir(source_repo / "skill-a", skills_dir / "skill-a", source_label="test/repo")

    record_install("test/repo", trial=True)

    cmd_list()
    output = capsys.readouterr().out
    assert "(trial)" in output


def test_project_skills_listed(
    env: Env, source_repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    project_skills = env.project / ".claude" / "skills"
    project_skills.mkdir(parents=True)
    (project_skills / "proj-skill").symlink_to(source_repo / "skill-a")

    cmd_list()
    output = capsys.readouterr().out
    assert "Project skills" in output


def test_lists_commands(env: Env, source_repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    commands_dir = env.home / ".claude" / "commands"
    commands_dir.mkdir(parents=True)
    (commands_dir / "do-thing.md").symlink_to(source_repo / "commands" / "do-thing.md")

    cmd_list()
    output = capsys.readouterr().out
    assert "Global commands" in output
    assert "do-thing.md (" not in output


def test_project_commands_listed(
    env: Env, source_repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    project_cmds = env.project / ".claude" / "commands"
    project_cmds.mkdir(parents=True)
    (project_cmds / "do-thing.md").symlink_to(source_repo / "commands" / "do-thing.md")

    cmd_list()
    output = capsys.readouterr().out
    assert "Project commands" in output


def test_available_no_sources(env: Env, capsys: pytest.CaptureFixture[str]) -> None:
    cmd_list(available=True)
    output = capsys.readouterr().out
    assert "No available skills found" in output


def test_available_lists_uninstalled_skills(
    env: Env, source_repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cache_dir = env.home / ".cache" / "skillset" / "repos" / "owner"
    cache_dir.mkdir(parents=True)
    (cache_dir / "repo").symlink_to(source_repo)

    cmd_list(available=True)
    output = capsys.readouterr().out
    assert "owner/repo" in output
    assert "skill-a" in output
    assert "skill-b" in output
    assert "2 skill(s) available" in output


def test_available_excludes_installed_skills(
    env: Env, source_repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cache_dir = env.home / ".cache" / "skillset" / "repos" / "owner"
    cache_dir.mkdir(parents=True)
    (cache_dir / "repo").symlink_to(source_repo)

    skills_dir = env.home / ".claude" / "skills"
    skills_dir.mkdir(parents=True)
    (skills_dir / "skill-a").symlink_to(source_repo / "skill-a")

    cmd_list(available=True)
    output = capsys.readouterr().out
    assert "skill-a" not in output
    assert "skill-b" in output
    assert "1 skill(s) available" in output


def test_available_excludes_project_installed_skills(
    env: Env, source_repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cache_dir = env.home / ".cache" / "skillset" / "repos" / "owner"
    cache_dir.mkdir(parents=True)
    (cache_dir / "repo").symlink_to(source_repo)

    project_skills = env.project / ".claude" / "skills"
    project_skills.mkdir(parents=True)
    (project_skills / "skill-a").symlink_to(source_repo / "skill-a")
    (project_skills / "skill-b").symlink_to(source_repo / "skill-b")

    cmd_list(available=True)
    output = capsys.readouterr().out
    assert "No available skills found" in output


def test_list_fallback_skillset_root(
    env: Env, source_repo: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """When not in a git repo but skillset.toml is found, use skillset root for project dirs."""
    monkeypatch.setattr("skillset.paths.get_git_root", lambda: None)
    monkeypatch.setattr("skillset.commands.list.find_skillset_root", lambda: env.project)

    skills_dir = env.project / ".claude" / "skills"
    skills_dir.mkdir(parents=True)
    (skills_dir / "skill-a").symlink_to(source_repo / "skill-a")

    cmd_list()
    output = capsys.readouterr().out
    assert "skill-a" in output
