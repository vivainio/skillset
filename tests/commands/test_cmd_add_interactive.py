"""Tests for skillset.commands.cmd_add interactive mode."""

from pathlib import Path
from unittest.mock import patch

import pytest

from skillset.commands import cmd_add
from tests.support import Env


def test_interactive_no_repo_selects_from_cache(
    env: Env, source_repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Without repo, -i presents cached repos via fzf."""
    cache_dir = env.home / ".cache" / "skillset" / "repos" / "owner" / "repo"
    cache_dir.mkdir(parents=True)
    for name in ("skill-a", "skill-b"):
        d = cache_dir / name
        d.mkdir()
        (d / "SKILL.md").write_text(f"# {name}\n")

    with patch("skillset.commands._resolve.fzf_select", return_value=["owner/repo"]) as fzf_repo:
        with patch("skillset.commands.add.fzf_select_skills", return_value=["skill-a"]):
            with patch("skillset.commands._resolve.clone_or_pull", return_value=cache_dir):
                with patch("skillset.commands._resolve.get_repo_dir", return_value=cache_dir):
                    with patch("skillset.commands._resolve.is_link", return_value=False):
                        cmd_add(interactive=True)

    fzf_repo.assert_called_once()
    call_args = fzf_repo.call_args
    prompt = call_args[1].get(
        "prompt",
        call_args[0][1] if len(call_args[0]) > 1 else "",
    )
    assert "Repo> " in prompt
    output = capsys.readouterr().out
    assert "Linked" in output


def test_interactive_no_cached_repos_exits(env: Env) -> None:
    """When no repos are cached, -i without repo exits."""
    with pytest.raises(SystemExit):
        cmd_add(interactive=True)


def test_interactive_fzf_empty_selection_returns(
    env: Env, source_repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """When fzf returns empty (user cancels), cmd_add returns silently."""
    cache_dir = env.home / ".cache" / "skillset" / "repos" / "owner" / "repo"
    cache_dir.mkdir(parents=True)

    with patch("skillset.commands._resolve.fzf_select", return_value=[]):
        cmd_add(interactive=True)

    output = capsys.readouterr().out
    assert output == ""


def test_interactive_with_repo_uses_fzf_for_skills(
    env: Env, source_repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """With repo + -i, fzf is used to select skills."""
    with patch("skillset.commands.add.fzf_select_skills", return_value=["skill-a"]):
        with patch("skillset.commands.add.fzf_select", return_value=[]):
            cmd_add(repo=str(source_repo), interactive=True)

    skills_dir = env.home / ".claude" / "skills"
    assert (skills_dir / "skill-a").is_symlink()
    assert not (skills_dir / "skill-b").exists()


def test_interactive_with_repo_selects_commands(
    env: Env, source_repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """With repo + -i, fzf is used to select commands too."""
    with patch("skillset.commands.add.fzf_select_skills", return_value=["skill-a"]):
        with patch("skillset.commands.add.fzf_select", return_value=["do-thing.md"]):
            cmd_add(repo=str(source_repo), interactive=True)

    commands_dir = env.home / ".claude" / "commands"
    assert (commands_dir / "do-thing.md").is_symlink()


def test_interactive_second_add_updates_yaml(
    env: Env, source_repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Adding a new skill from an already-registered source folds it into enabled."""
    from skillset.paths import load_skillset

    yaml_path = env.home / ".claude" / "skillset.yaml"
    yaml_path.write_text("skills: {}\n")

    # First add: select skill-a. skill-b lands in disabled.
    with patch("skillset.commands.add.fzf_select_skills", return_value=["skill-a"]):
        with patch("skillset.commands.add.fzf_select", return_value=[]):
            cmd_add(repo=str(source_repo), interactive=True)

    config = load_skillset(yaml_path)
    entry_key = next(iter(config["skills"]))
    entry = config["skills"][entry_key]
    assert list(entry["enabled"]) == ["skill-a"]
    assert list(entry.get("disabled", [])) == ["skill-b"]

    # Second add: select skill-b. It should move from disabled to enabled.
    with patch("skillset.commands.add.fzf_select_skills", return_value=["skill-b"]):
        with patch("skillset.commands.add.fzf_select", return_value=[]):
            cmd_add(repo=str(source_repo), interactive=True)

    config = load_skillset(yaml_path)
    entry = config["skills"][entry_key]
    assert "skill-a" in entry["enabled"]
    assert "skill-b" in entry["enabled"]
    assert "skill-b" not in entry.get("disabled", [])


def test_interactive_no_available_skills(
    env: Env, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Interactive mode with repo that has no skills."""
    empty = tmp_path / "empty"
    empty.mkdir()

    with patch("skillset.commands.add.fzf_select", return_value=[]):
        cmd_add(repo=str(empty), interactive=True)

    output = capsys.readouterr().out
    assert "No skills found in repo" in output
