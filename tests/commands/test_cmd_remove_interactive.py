"""Tests for skillset.commands.cmd_remove interactive mode."""

from unittest.mock import patch

from skillset.commands import cmd_remove
from skillset.paths import load_skillset


def test_interactive_selects_skills_to_remove(env, source_repo, capsys):
    skills_dir = env.home / ".claude" / "skills"
    skills_dir.mkdir(parents=True)
    (skills_dir / "skill-a").symlink_to(source_repo / "skill-a")
    (skills_dir / "skill-b").symlink_to(source_repo / "skill-b")

    with patch("skillset.commands.remove.fzf_select_installed_skills", return_value=["skill-a"]):
        cmd_remove(interactive=True)

    assert not (skills_dir / "skill-a").exists()
    assert (skills_dir / "skill-b").is_symlink()
    output = capsys.readouterr().out
    assert "Removed skill-a" in output


def test_interactive_removes_multiple(env, source_repo, capsys):
    skills_dir = env.home / ".claude" / "skills"
    skills_dir.mkdir(parents=True)
    (skills_dir / "skill-a").symlink_to(source_repo / "skill-a")
    (skills_dir / "skill-b").symlink_to(source_repo / "skill-b")

    with patch(
        "skillset.commands.remove.fzf_select_installed_skills",
        return_value=["skill-a", "skill-b"],
    ):
        cmd_remove(interactive=True)

    assert not (skills_dir / "skill-a").exists()
    assert not (skills_dir / "skill-b").exists()


def test_interactive_persists_disabled_skills(env, source_repo):
    skills_dir = env.home / ".claude" / "skills"
    skills_dir.mkdir(parents=True)
    (skills_dir / "skill-a").symlink_to(source_repo / "skill-a")
    (skills_dir / "skill-b").symlink_to(source_repo / "skill-b")
    config_path = env.home / ".claude" / "skillset.yaml"
    config_path.write_text(
        f"skills:\n  owner/repo:\n    editable: true\n"
        f"    source: {source_repo}\n    enabled: ['*']\n"
    )

    with patch("skillset.commands.remove.fzf_select_installed_skills", return_value=["skill-a"]):
        cmd_remove(interactive=True)

    entry = load_skillset(config_path)["skills"]["owner/repo"]
    assert list(entry["enabled"]) == ["*"]
    assert list(entry["disabled"]) == ["skill-a"]


def test_interactive_empty_selection(env, source_repo, capsys):
    """When fzf returns empty, nothing is removed."""
    skills_dir = env.home / ".claude" / "skills"
    skills_dir.mkdir(parents=True)
    (skills_dir / "skill-a").symlink_to(source_repo / "skill-a")

    with patch("skillset.commands.remove.fzf_select_installed_skills", return_value=[]):
        cmd_remove(interactive=True)

    assert (skills_dir / "skill-a").is_symlink()


def test_interactive_no_managed_skills(env, capsys):
    """When no skills exist, prints message and returns."""
    skills_dir = env.home / ".claude" / "skills"
    skills_dir.mkdir(parents=True)

    cmd_remove(interactive=True)

    output = capsys.readouterr().out
    assert "No skills" in output


def test_interactive_no_skills_dir(env, capsys):
    """When skills dir doesn't exist, prints message and returns."""
    cmd_remove(interactive=True)

    output = capsys.readouterr().out
    assert "No skills" in output


def test_interactive_removes_selected_unmanaged_skill(env):
    skills_dir = env.home / ".claude" / "skills"
    unmanaged = skills_dir / "personal"
    unmanaged.mkdir(parents=True)
    (unmanaged / "SKILL.md").write_text("# Personal\n")

    with patch(
        "skillset.commands.remove.fzf_select_installed_skills",
        return_value=["personal"],
    ) as select:
        cmd_remove(interactive=True)

    assert not unmanaged.exists()
    assert select.call_args.args[0] == [unmanaged]


def test_interactive_shows_scope_in_prompt(env, source_repo, capsys, monkeypatch):
    """Interactive mode shows 'project' scope when in local context."""
    monkeypatch.setattr("skillset.commands.remove.find_skillset_root", lambda: env.project)
    project_skills = env.project / ".claude" / "skills"
    project_skills.mkdir(parents=True)
    (project_skills / "skill-a").symlink_to(source_repo / "skill-a")

    with patch(
        "skillset.commands.remove.fzf_select_installed_skills", return_value=["skill-a"]
    ) as mock:
        cmd_remove(interactive=True)

    call_args = mock.call_args
    prompt = call_args[1].get(
        "prompt",
        call_args[0][1] if len(call_args[0]) > 1 else "",
    )
    assert "project" in prompt


def test_interactive_global_scope_prompt(env, source_repo, capsys):
    """Interactive mode shows 'global' scope when not in local context."""
    skills_dir = env.home / ".claude" / "skills"
    skills_dir.mkdir(parents=True)
    (skills_dir / "skill-a").symlink_to(source_repo / "skill-a")

    with patch(
        "skillset.commands.remove.fzf_select_installed_skills", return_value=["skill-a"]
    ) as mock:
        cmd_remove(interactive=True)

    call_args = mock.call_args
    prompt = call_args[1].get(
        "prompt",
        call_args[0][1] if len(call_args[0]) > 1 else "",
    )
    assert "global" in prompt
