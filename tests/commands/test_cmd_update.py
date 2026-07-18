"""Tests for skillset.commands.cmd_update."""

import subprocess
from unittest.mock import patch

import pytest

from skillset.commands import cmd_update
from skillset.commands.update import _changed_skill_names


def test_no_file_exits(env):
    with pytest.raises(SystemExit):
        cmd_update()


def test_empty_skills_section(env, capsys):
    yaml_file = env.home / ".claude" / "skillset.yaml"
    yaml_file.write_text("skills: {}\n")

    cmd_update()
    output = capsys.readouterr().out
    assert "No skills entries" in output


def test_sync_wildcard_entry(env, source_repo, capsys):
    yaml_file = env.home / ".claude" / "skillset.yaml"
    yaml_file.write_text("skills:\n  owner/repo:\n    enabled: ['*']\n")

    with patch("skillset.commands.update.clone_or_pull", return_value=source_repo):
        cmd_update()

    output = capsys.readouterr().out
    assert "Updating owner/repo" in output
    assert "skill-a" in output


def test_sync_glob_pattern_matches(env, source_repo, capsys):
    """enabled = ["skill-*"] expands to every skill in source (both skill-a and skill-b)."""
    yaml_file = env.home / ".claude" / "skillset.yaml"
    yaml_file.write_text("skills:\n  owner/repo:\n    enabled: ['skill-*']\n")

    with patch("skillset.commands.update.clone_or_pull", return_value=source_repo):
        cmd_update()

    output = capsys.readouterr().out
    assert "+ skill-a" in output
    assert "+ skill-b" in output


def test_sync_glob_with_disabled_subtraction(env, source_repo, capsys):
    """Pattern on enabled minus an explicit disabled entry."""
    yaml_file = env.home / ".claude" / "skillset.yaml"
    yaml_file.write_text(
        "skills:\n  owner/repo:\n    enabled: ['skill-*']\n    disabled: [skill-b]\n"
    )

    with patch("skillset.commands.update.clone_or_pull", return_value=source_repo):
        cmd_update()

    output = capsys.readouterr().out
    assert "+ skill-a" in output
    assert "+ skill-b" not in output


def test_sync_glob_does_not_cover_unrelated_new_skills(env, source_repo, capsys):
    """enabled=['skill-a*'] only covers skill-a; skill-b is still new and prompts."""
    yaml_file = env.home / ".claude" / "skillset.yaml"
    yaml_file.write_text("skills:\n  owner/repo:\n    enabled: ['skill-a*']\n")

    with patch("skillset.commands.update.clone_or_pull", return_value=source_repo):
        with patch("builtins.input", return_value="n"):
            cmd_update()

    output = capsys.readouterr().out
    assert "+ skill-a" in output
    assert "New skills detected" in output
    assert "skill-b" in output


def test_sync_all_disabled_links_nothing(env, source_repo, capsys):
    """enabled=[] with every source skill in disabled links nothing and does not prompt."""
    yaml_file = env.home / ".claude" / "skillset.yaml"
    yaml_file.write_text(
        "skills:\n  owner/repo:\n    enabled: []\n    disabled: [skill-a, skill-b]\n"
    )

    with patch("skillset.commands.update.clone_or_pull", return_value=source_repo):
        cmd_update()

    output = capsys.readouterr().out
    assert "Update complete (0 skill(s) changed)" in output
    assert "New skills detected" not in output


def test_sync_invalid_repo_spec(env, capsys):
    yaml_file = env.home / ".claude" / "skillset.yaml"
    yaml_file.write_text("skills:\n  invalid:\n    enabled: ['*']\n")

    cmd_update()
    output = capsys.readouterr().out
    assert "Invalid repo format" in output


def test_sync_dict_entry_all_skills(env, source_repo, capsys):
    yaml_file = env.home / ".claude" / "skillset.yaml"
    yaml_file.write_text("skills:\n  owner/repo:\n    enabled: ['*']\n")

    with patch("skillset.commands.update.clone_or_pull", return_value=source_repo):
        cmd_update()

    output = capsys.readouterr().out
    assert "Updating owner/repo" in output


def test_sync_selective_skills(env, source_repo, capsys):
    yaml_file = env.home / ".claude" / "skillset.yaml"
    yaml_file.write_text(
        "skills:\n  owner/repo:\n    enabled: [skill-a]\n    disabled: [skill-b]\n"
    )

    with patch("skillset.commands.update.clone_or_pull", return_value=source_repo):
        cmd_update()

    output = capsys.readouterr().out
    assert "skill-a" in output


def test_sync_detects_new_skills(env, source_repo, capsys):
    yaml_file = env.home / ".claude" / "skillset.yaml"
    # Only track skill-a, leaving skill-b as "new"
    yaml_file.write_text("skills:\n  owner/repo:\n    enabled: [skill-a]\n")

    with patch("skillset.commands.update.clone_or_pull", return_value=source_repo):
        with patch("builtins.input", return_value="n"):
            cmd_update()

    output = capsys.readouterr().out
    assert "New skills detected" in output
    assert "skill-b" in output


def test_sync_removes_excluded_skills(env, source_repo, capsys):
    skills_dir = env.home / ".claude" / "skills"
    skills_dir.mkdir(parents=True)
    (skills_dir / "skill-b").symlink_to(source_repo / "skill-b")

    yaml_file = env.home / ".claude" / "skillset.yaml"
    yaml_file.write_text(
        "skills:\n  owner/repo:\n    enabled: [skill-a]\n    disabled: [skill-b]\n"
    )

    with patch("skillset.commands.update.clone_or_pull", return_value=source_repo):
        cmd_update()

    assert not (skills_dir / "skill-b").exists()
    output = capsys.readouterr().out
    assert "skill-b" not in output


def test_sync_does_not_remove_excluded_skill_owned_by_other_source(env, source_repo, tmp_path):
    other_source = tmp_path / "other-source"
    other_skill = other_source / "skill-b"
    other_skill.mkdir(parents=True)
    (other_skill / "SKILL.md").write_text("# other skill-b\n")
    skills_dir = env.home / ".claude" / "skills"
    skills_dir.mkdir(parents=True)
    installed = skills_dir / "skill-b"
    installed.symlink_to(other_skill)

    yaml_file = env.home / ".claude" / "skillset.yaml"
    yaml_file.write_text(
        "skills:\n  owner/repo:\n    enabled: [skill-a]\n    disabled: [skill-b]\n"
    )

    with patch("skillset.commands.update.clone_or_pull", return_value=source_repo):
        cmd_update()

    assert installed.is_symlink()
    assert installed.resolve() == other_skill


def test_sync_reports_only_skills_changed_by_pull(env, source_repo, capsys):
    skills_dir = env.home / ".claude" / "skills"
    skills_dir.mkdir(parents=True)
    for name in ("skill-a", "skill-b"):
        (skills_dir / name).symlink_to(source_repo / name)

    yaml_file = env.home / ".claude" / "skillset.yaml"
    yaml_file.write_text("skills:\n  owner/repo:\n    enabled: ['*']\n")

    resolved = (source_repo, source_repo, "owner", "repo", {"skill-a"})
    with patch("skillset.commands.update._resolve_update_source", return_value=resolved):
        cmd_update()

    output = capsys.readouterr().out
    assert "~ skill-a (updated)" in output
    assert "skill-b" not in output


def test_changed_skill_names_maps_git_changes_to_skill_dirs(source_repo):
    subprocess.run(["git", "init", "-q"], cwd=source_repo, check=True)
    subprocess.run(["git", "add", "."], cwd=source_repo, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.com",
            "commit",
            "-qm",
            "first",
        ],
        cwd=source_repo,
        check=True,
    )
    old_head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=source_repo,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    (source_repo / "skill-a" / "SKILL.md").write_text("# changed\n")
    (source_repo / "commands" / "do-thing.md").write_text("# changed command\n")
    subprocess.run(["git", "add", "."], cwd=source_repo, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.com",
            "commit",
            "-qm",
            "second",
        ],
        cwd=source_repo,
        check=True,
    )

    assert _changed_skill_names(source_repo, source_repo, old_head) == {"skill-a"}


def test_sync_editable(env, source_repo, capsys):
    yaml_file = env.home / ".claude" / "skillset.yaml"
    yaml_file.write_text(f"skills:\n  my-lib:\n    editable: true\n    source: {source_repo}\n")

    cmd_update()
    output = capsys.readouterr().out
    assert "editable" in output


def test_sync_editable_missing_source(env, capsys):
    yaml_file = env.home / ".claude" / "skillset.yaml"
    yaml_file.write_text("skills:\n  my-lib:\n    editable: true\n")

    cmd_update()
    output = capsys.readouterr().out
    assert "requires 'source' path" in output


def test_sync_editable_source_not_found(env, capsys):
    yaml_file = env.home / ".claude" / "skillset.yaml"
    yaml_file.write_text("skills:\n  my-lib:\n    editable: true\n    source: /nonexistent\n")

    cmd_update()
    output = capsys.readouterr().out
    assert "Source not found" in output
    assert output.count("Source not found") == 2
    assert "--- Update notices ---" in output
    assert "skillset update --repair" in output


def test_repair_disables_unmanaged_destination_without_removing_it(env, source_repo, capsys):
    skills_dir = env.home / ".claude" / "skills"
    unmanaged = skills_dir / "skill-a"
    unmanaged.mkdir(parents=True)
    (unmanaged / "SKILL.md").write_text("# user-owned\n")
    yaml_file = env.home / ".claude" / "skillset.yaml"
    yaml_file.write_text("skills:\n  owner/repo:\n    enabled: ['*']\n")

    with patch("skillset.commands.update.clone_or_pull", return_value=source_repo):
        cmd_update(repair=True)

    from skillset.paths import load_skillset

    config = load_skillset(yaml_file)
    assert config["unmanaged"] == ["skill-a"]
    assert "disabled" not in config["skills"]["owner/repo"]
    assert unmanaged.is_dir()
    assert not unmanaged.is_symlink()
    assert "Marked skill-a unmanaged" in capsys.readouterr().out

    with patch("skillset.commands.update.clone_or_pull", return_value=source_repo):
        cmd_update()
    assert "skill-a" not in capsys.readouterr().out


def test_sync_invalid_value_type(env, capsys):
    yaml_file = env.home / ".claude" / "skillset.yaml"
    yaml_file.write_text("skills:\n  repo: 42\n")

    cmd_update()
    output = capsys.readouterr().out
    assert "must be a sub-table" in output


def test_sync_with_path(env, source_repo, capsys):
    sub = source_repo / "sub"
    skill = sub / "nested-skill"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("# nested\n")

    yaml_file = env.home / ".claude" / "skillset.yaml"
    yaml_file.write_text("skills:\n  owner/repo:\n    path: sub\n")

    with patch("skillset.commands.update.clone_or_pull", return_value=source_repo):
        cmd_update()

    output = capsys.readouterr().out
    assert "nested-skill" in output


def test_sync_path_not_found_in_repo(env, source_repo, capsys):
    yaml_file = env.home / ".claude" / "skillset.yaml"
    yaml_file.write_text("skills:\n  owner/repo:\n    path: nonexistent\n")

    with patch("skillset.commands.update.clone_or_pull", return_value=source_repo):
        cmd_update()

    output = capsys.readouterr().out
    assert "Path not found in repo" in output


def test_sync_editable_path_not_found(env, source_repo, capsys):
    yaml_file = env.home / ".claude" / "skillset.yaml"
    yaml_file.write_text(
        "skills:\n"
        "  my-lib:\n"
        "    editable: true\n"
        f"    source: {source_repo}\n"
        "    path: nonexistent\n"
    )

    cmd_update()
    output = capsys.readouterr().out
    assert "Path not found" in output


def test_sync_with_file_arg(env, source_repo, capsys):
    """Explicit file argument to cmd_update."""
    yaml_file = env.tmp / "custom.yaml"
    yaml_file.write_text(f"skills:\n  {source_repo}:\n    enabled: ['*']\n")

    with patch("builtins.input", return_value="y"):
        cmd_update(file=str(yaml_file))

    output = capsys.readouterr().out
    assert "Updating" in output


def test_sync_global_flag(env, source_repo, capsys):
    """cmd_update(g=True) uses global skillset.yaml."""
    yaml_file = env.home / ".claude" / "skillset.yaml"
    yaml_file.write_text(f"skills:\n  {source_repo}:\n    enabled: ['*']\n")

    with patch("builtins.input", return_value="y"):
        cmd_update(g=True)

    output = capsys.readouterr().out
    assert "Updating" in output


def test_sync_local_scope(env, source_repo, capsys, monkeypatch):
    """Sync with local skillset.yaml found via find_skillset_root."""
    monkeypatch.setattr("skillset.commands.update.find_skillset_root", lambda: env.project)
    yaml_file = env.project / "skillset.yaml"
    yaml_file.write_text(f"skills:\n  {source_repo}:\n    enabled: ['*']\n")

    project_skills = env.project / ".claude" / "skills"
    project_skills.mkdir(parents=True)
    (env.project / ".claude" / "commands").mkdir(parents=True)

    with patch("builtins.input", return_value="y"):
        cmd_update()

    output = capsys.readouterr().out
    assert "Updating" in output


def test_sync_editable_relative_source_from_local_yaml_dir(env, capsys, monkeypatch):
    """Relative editable `source` resolves against the yaml's dir, not the CWD."""
    monkeypatch.setattr("skillset.commands.update.find_skillset_root", lambda: env.project)
    sibling = env.project.parent / "bt-docs"
    (sibling / "some-skill").mkdir(parents=True)
    (sibling / "some-skill" / "SKILL.md").write_text("---\nname: some-skill\n---\n")

    yaml_file = env.project / "skillset.yaml"
    yaml_file.write_text("skills:\n  bt-docs:\n    editable: true\n    source: ../bt-docs\n")

    (env.project / ".claude" / "skills").mkdir(parents=True)
    (env.project / ".claude" / "commands").mkdir(parents=True)

    subdir = env.project / "subdir"
    subdir.mkdir()
    monkeypatch.chdir(subdir)

    cmd_update()
    output = capsys.readouterr().out
    assert "Source not found" not in output
    assert (env.project / ".claude" / "skills" / "some-skill").is_symlink()


def test_sync_local_file_not_found(env, capsys, monkeypatch):
    """Local sync file not found shows local hint."""
    monkeypatch.setattr("skillset.commands.update.find_skillset_root", lambda: env.project)

    with pytest.raises(SystemExit):
        cmd_update()

    output = capsys.readouterr().out
    assert "Run 'skillset init' to create one." in output


def test_sync_dict_invalid_repo_spec(env, capsys):
    """Dict entry with invalid repo spec in non-editable mode."""
    yaml_file = env.home / ".claude" / "skillset.yaml"
    yaml_file.write_text("skills:\n  invalid:\n    copy: true\n")

    cmd_update()
    output = capsys.readouterr().out
    assert "Invalid repo format" in output


def test_links_section(env, capsys):
    yaml_file = env.home / ".claude" / "skillset.yaml"
    target = env.tmp / "target_file"
    target.write_text("content")
    link_path = env.project / "mylink"

    yaml_file.write_text(f"skills: {{}}\nlinks:\n  {link_path}: {target}\n")

    with patch("skillset.commands.update.subprocess.run") as mock_run:
        mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=1)
        cmd_update()

    output = capsys.readouterr().out
    assert "Linked" in output


def test_links_existing_symlink(env, capsys):
    yaml_file = env.home / ".claude" / "skillset.yaml"
    target = env.tmp / "target"
    target.write_text("x")
    link_path = env.project / "mylink"
    link_path.symlink_to(target)

    yaml_file.write_text(f"skills: {{}}\nlinks:\n  {link_path}: {target}\n")

    with patch("skillset.commands.update.subprocess.run") as mock_run:
        mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0)
        cmd_update()

    output = capsys.readouterr().out
    assert "already exists" in output


def test_links_existing_file_skipped(env, capsys):
    yaml_file = env.home / ".claude" / "skillset.yaml"
    target = env.tmp / "target"
    target.write_text("x")
    existing = env.project / "myfile"
    existing.write_text("real file")

    yaml_file.write_text(f"skills: {{}}\nlinks:\n  {existing}: {target}\n")

    with patch("skillset.commands.update.subprocess.run") as mock_run:
        mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0)
        cmd_update()

    output = capsys.readouterr().out
    assert "Skipping" in output


def test_snapshot_entry_skipped(env, capsys):
    """Entries with snapshot: true must not be cloned, pulled, or relinked."""
    yaml_file = env.home / ".claude" / "skillset.yaml"
    yaml_file.write_text(
        "skills:\n"
        "  owner/repo:\n"
        "    snapshot: true\n"
        "    ref: abcdef1234567890\n"
        "    enabled: ['*']\n"
    )

    with patch("skillset.commands.update.clone_or_pull") as mock_clone:
        cmd_update()
        mock_clone.assert_not_called()

    output = capsys.readouterr().out
    assert "Skipping owner/repo" in output
    assert "snapshot" in output
