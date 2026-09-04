"""Tests for skillset.commands.cmd_add."""

from pathlib import Path
from unittest.mock import patch

import pytest

from skillset.commands import cmd_add
from tests.support import Env


def test_add_from_local_path(
    env: Env, source_repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    with patch("builtins.input", return_value="y"):
        cmd_add(repo=str(source_repo))

    skills_dir = env.home / ".claude" / "skills"
    assert (skills_dir / "skill-a").is_symlink()
    assert (skills_dir / "skill-b").is_symlink()
    output = capsys.readouterr().out
    assert "Linked" in output


def test_add_local_subdir_reuses_registered_editable_root(env: Env, source_repo: Path) -> None:
    yaml_path = env.home / ".claude" / "skillset.yaml"
    yaml_path.write_text(
        "skills:\n"
        "  owner/repo:\n"
        "    editable: true\n"
        f"    source: {source_repo.parent}\n"
        "    enabled: [existing]\n"
    )

    cmd_add(repo=str(source_repo), skills=["skill-a"])

    from skillset.paths import load_skillset

    entries = load_skillset(yaml_path)["skills"]
    assert list(entries) == ["owner/repo"]
    assert set(entries["owner/repo"]["enabled"]) == {"existing", "skill-a"}


def test_add_with_skill_filter(
    env: Env, source_repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cmd_add(repo=str(source_repo), skills=["skill-a"])

    skills_dir = env.home / ".claude" / "skills"
    assert (skills_dir / "skill-a").is_symlink()
    assert not (skills_dir / "skill-b").exists()


def test_add_copy_mode(env: Env, source_repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    with patch("builtins.input", return_value="y"):
        cmd_add(repo=str(source_repo), copy=True)

    skills_dir = env.home / ".claude" / "skills"
    assert (skills_dir / "skill-a").is_dir()
    assert not (skills_dir / "skill-a").is_symlink()
    output = capsys.readouterr().out
    assert "Copied" in output


def test_add_from_owner_repo(
    env: Env, source_repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    with patch("skillset.commands._resolve.clone_or_pull", return_value=source_repo):
        with patch("skillset.commands._resolve.get_repo_dir", return_value=source_repo):
            with patch("skillset.commands._resolve.is_link", return_value=False):
                with patch("builtins.input", return_value="y"):
                    cmd_add(repo="owner/repo")

    output = capsys.readouterr().out
    assert "Linked" in output


def test_add_no_repo_exits(env: Env) -> None:
    with pytest.raises(SystemExit):
        cmd_add()


def test_add_fetch_links_nothing(
    env: Env, source_repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cmd_add(repo=str(source_repo), fetch=True)

    skills_dir = env.home / ".claude" / "skills"
    assert not skills_dir.exists() or not any(skills_dir.iterdir())
    output = capsys.readouterr().out
    assert "Fetched" in output


def test_add_fetch_registers_with_no_skills_enabled(env: Env, source_repo: Path) -> None:
    cmd_add(repo=str(source_repo), fetch=True)

    toml_path = env.home / ".claude" / "skillset.yaml"
    from skillset.paths import load_skillset

    data = load_skillset(toml_path)
    entry = next(iter(data["skills"].values()))
    assert entry["enabled"] == []
    assert set(entry["disabled"]) == {"skill-a", "skill-b"}


def test_add_global_flag_skips_local_detection(
    env: Env, source_repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """With --global, skills go to global dir even when skillset.toml exists."""
    with patch("builtins.input", return_value="y"):
        cmd_add(repo=str(source_repo), g=True)

    skills_dir = env.home / ".claude" / "skills"
    assert (skills_dir / "skill-a").is_symlink()


def test_add_local_path_not_found_exits(env: Env) -> None:
    with pytest.raises(SystemExit):
        cmd_add(repo="/nonexistent/path")


def test_add_invalid_github_url_exits(env: Env) -> None:
    with pytest.raises(SystemExit):
        cmd_add(repo="https://gitlab.com/owner/repo")


def test_add_invalid_repo_spec_exits(env: Env) -> None:
    with pytest.raises(SystemExit):
        cmd_add(repo="invalid-spec")


def test_add_with_subpath(env: Env, source_repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    # Create a subpath
    sub = source_repo / "sub"
    skill = sub / "sub-skill"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("# sub-skill\n")

    with patch("builtins.input", return_value="y"):
        cmd_add(repo=str(source_repo), subpath="sub")

    skills_dir = env.home / ".claude" / "skills"
    assert (skills_dir / "sub-skill").is_symlink()


def test_add_subpath_not_found_exits(env: Env, source_repo: Path) -> None:
    with pytest.raises(SystemExit):
        cmd_add(repo=str(source_repo), subpath="nonexistent")


def test_add_no_cache_mode(env: Env, source_repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    with patch("skillset.commands._resolve.clone_to_temp", return_value=source_repo):
        with patch("builtins.input", return_value="y"):
            cmd_add(repo="owner/repo", no_cache=True)

    output = capsys.readouterr().out
    assert "Copied" in output


def test_add_github_url(env: Env, source_repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    with patch("skillset.commands._resolve.clone_or_pull", return_value=source_repo):
        with patch("skillset.commands._resolve.get_repo_dir", return_value=source_repo):
            with patch("skillset.commands._resolve.is_link", return_value=False):
                with patch("builtins.input", return_value="y"):
                    cmd_add(repo="https://github.com/owner/repo")

    output = capsys.readouterr().out
    assert "Linked" in output


def test_add_trial(env: Env, source_repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    with patch("builtins.input", return_value="y"):
        cmd_add(repo=str(source_repo), trial=True)

    from skillset.manifest import load_manifest

    manifest = load_manifest()
    for key, opts in manifest.items():
        assert opts.get("trial") is True


def test_add_skill_by_name(env: Env, source_repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    # Set up skillset.yaml with editable entry
    yaml_path = env.home / ".claude" / "skillset.yaml"
    yaml_path.write_text(f"skills:\n  my-lib:\n    editable: true\n    source: {source_repo}\n")

    cmd_add(repo="skill-a")

    skills_dir = env.home / ".claude" / "skills"
    assert (skills_dir / "skill-a").is_symlink()


def test_add_skill_name_not_found_exits(env: Env) -> None:
    yaml_path = env.home / ".claude" / "skillset.yaml"
    yaml_path.write_text("skills: {}\n")

    with pytest.raises(SystemExit):
        cmd_add(repo="nonexistent")


def test_add_glob_filter_persists_pattern(
    env: Env, source_repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A glob in -s links matching skills and persists the pattern (not the
    expanded names) so `update` re-expands it later. `%` is the shell-safe alias."""
    yaml_path = env.home / ".claude" / "skillset.yaml"
    yaml_path.write_text("skills: {}\n")

    with patch("skillset.commands._resolve.clone_or_pull", return_value=source_repo):
        with patch("skillset.commands._resolve.get_repo_dir", return_value=source_repo):
            with patch("skillset.commands._resolve.is_link", return_value=False):
                cmd_add(repo="owner/repo", skills=["skill-%"])

    skills_dir = env.home / ".claude" / "skills"
    assert (skills_dir / "skill-a").is_symlink()
    assert (skills_dir / "skill-b").is_symlink()

    from skillset.paths import load_skillset

    entry = load_skillset(yaml_path)["skills"]["owner/repo"]
    assert entry["enabled"] == ["skill-*"]


def test_add_registers_in_skillset_yaml(
    env: Env, source_repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    yaml_path = env.home / ".claude" / "skillset.yaml"
    yaml_path.write_text("skills: {}\n")

    with patch("skillset.commands._resolve.clone_or_pull", return_value=source_repo):
        with patch("skillset.commands._resolve.get_repo_dir", return_value=source_repo):
            with patch("skillset.commands._resolve.is_link", return_value=False):
                with patch("builtins.input", return_value="y"):
                    cmd_add(repo="owner/repo")

    from skillset.paths import load_skillset

    data = load_skillset(yaml_path)
    assert "owner/repo" in data.get("skills", {})


def test_add_empty_repo_reports_nothing(
    env: Env, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    empty_repo = tmp_path / "empty"
    empty_repo.mkdir()

    cmd_add(repo=str(empty_repo))

    output = capsys.readouterr().out
    assert "No skills found in repo" in output


def test_add_agents_from_subpath(env: Env, tmp_path: Path) -> None:
    repo = tmp_path / "repo-with-packages"
    selected = repo / "package-a" / "agents" / "review"
    selected.mkdir(parents=True)
    (selected / "security.md").write_text("# security\n")
    other = repo / "package-b" / "agents"
    other.mkdir(parents=True)
    (other / "tester.md").write_text("# tester\n")

    cmd_add(repo=str(repo), subpath="package-a")

    agents_dir = env.home / ".claude" / "agents"
    assert (agents_dir / "review" / "security.md").is_symlink()
    assert not (agents_dir / "tester.md").exists()


def test_add_agents_with_glob(env: Env, tmp_path: Path) -> None:
    repo = tmp_path / "agent-source"
    root = repo / "agents"
    root.mkdir(parents=True)
    for name in ("review-code", "review-security", "tester"):
        (root / f"{name}.md").write_text(f"# {name}\n")

    cmd_add(repo=str(repo), agents=["review-%"])

    agents_dir = env.home / ".claude" / "agents"
    assert (agents_dir / "review-code.md").is_symlink()
    assert (agents_dir / "review-security.md").is_symlink()
    assert not (agents_dir / "tester.md").exists()

    from skillset.paths import load_skillset

    entry = next(iter(load_skillset(env.home / ".claude" / "skillset.yaml")["skills"].values()))
    assert entry["agents"] == ["review-*"]


def test_add_with_command_filter(env: Env, tmp_path: Path) -> None:
    repo = tmp_path / "command-source"
    root = repo / "commands"
    root.mkdir(parents=True)
    for name in ("run-ci-here", "deploy"):
        (root / f"{name}.md").write_text(f"# {name}\n")

    cmd_add(repo=str(repo), commands=["run-ci-here"])

    commands_dir = env.home / ".claude" / "commands"
    assert (commands_dir / "run-ci-here.md").is_symlink()
    assert not (commands_dir / "deploy.md").exists()


def test_add_commands_with_glob(env: Env, tmp_path: Path) -> None:
    repo = tmp_path / "command-source"
    root = repo / "commands"
    root.mkdir(parents=True)
    for name in ("review-code", "review-security", "tester"):
        (root / f"{name}.md").write_text(f"# {name}\n")

    cmd_add(repo=str(repo), commands=["review-%"])

    commands_dir = env.home / ".claude" / "commands"
    assert (commands_dir / "review-code.md").is_symlink()
    assert (commands_dir / "review-security.md").is_symlink()
    assert not (commands_dir / "tester.md").exists()

    from skillset.paths import load_skillset

    entry = next(iter(load_skillset(env.home / ".claude" / "skillset.yaml")["skills"].values()))
    assert entry["commands"] == ["review-*"]


def test_add_command_filter_replaces_existing_policy(env: Env, tmp_path: Path) -> None:
    repo = tmp_path / "command-source"
    root = repo / "commands"
    root.mkdir(parents=True)
    for name in ("run-ci-here", "deploy"):
        (root / f"{name}.md").write_text(f"# {name}\n")

    cmd_add(repo=str(repo))
    cmd_add(repo=str(repo), commands=["run-ci-here"])

    commands_dir = env.home / ".claude" / "commands"
    assert (commands_dir / "run-ci-here.md").is_symlink()
    assert not (commands_dir / "deploy.md").exists()

    from skillset.paths import load_skillset

    entry = next(iter(load_skillset(env.home / ".claude" / "skillset.yaml")["skills"].values()))
    assert entry["commands"] == ["run-ci-here"]


def test_add_command_name_not_found(
    env: Env, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = tmp_path / "command-source"
    root = repo / "commands"
    root.mkdir(parents=True)
    (root / "deploy.md").write_text("# deploy\n")

    cmd_add(repo=str(repo), commands=["missing"])

    output = capsys.readouterr().out
    assert "Command 'missing' not found" in output
    commands_dir = env.home / ".claude" / "commands"
    assert not (commands_dir / "deploy.md").exists()


def test_add_agent_filter_replaces_existing_policy(env: Env, tmp_path: Path) -> None:
    repo = tmp_path / "agent-source"
    root = repo / "agents"
    root.mkdir(parents=True)
    for name in ("reviewer", "tester"):
        (root / f"{name}.md").write_text(f"# {name}\n")

    cmd_add(repo=str(repo))
    cmd_add(repo=str(repo), agents=["reviewer"])

    agents_dir = env.home / ".claude" / "agents"
    assert (agents_dir / "reviewer.md").is_symlink()
    assert not (agents_dir / "tester.md").exists()

    from skillset.paths import load_skillset

    entry = next(iter(load_skillset(env.home / ".claude" / "skillset.yaml")["skills"].values()))
    assert entry["agents"] == ["reviewer"]


def test_add_links_skills_from_repo_with_settings(
    env: Env, source_repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Skills are linked even when repo contains a settings.json."""
    import json

    (source_repo / "settings.json").write_text(
        json.dumps({"permissions": {"allow": ["Bash(git *)"]}})
    )

    with patch("builtins.input", return_value="y"):
        cmd_add(repo=str(source_repo))

    output = capsys.readouterr().out
    assert "Linked" in output


def test_add_github_url_no_cache(
    env: Env, source_repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    with patch("skillset.commands._resolve.clone_to_temp", return_value=source_repo):
        with patch("builtins.input", return_value="y"):
            cmd_add(repo="https://github.com/owner/repo", no_cache=True)

    output = capsys.readouterr().out
    assert "Copied" in output


def test_add_linked_repo_dir(
    env: Env, source_repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """When repo_dir is already a symlink, resolve it."""
    cache_dir = env.home / ".cache" / "skillset" / "repos" / "owner"
    cache_dir.mkdir(parents=True)
    (cache_dir / "repo").symlink_to(source_repo)

    with patch("skillset.commands._resolve.clone_or_pull", return_value=source_repo):
        with patch("builtins.input", return_value="y"):
            cmd_add(repo="owner/repo")

    output = capsys.readouterr().out
    assert "Linked" in output


def test_add_github_url_linked_repo(
    env: Env, source_repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """GitHub URL when cached repo is a symlink."""
    cache_dir = env.home / ".cache" / "skillset" / "repos" / "owner"
    cache_dir.mkdir(parents=True)
    (cache_dir / "repo").symlink_to(source_repo)

    with patch("skillset.commands._resolve.get_repo_dir", return_value=cache_dir / "repo"):
        with patch("builtins.input", return_value="y"):
            cmd_add(repo="https://github.com/owner/repo")

    output = capsys.readouterr().out
    assert "Linked" in output


def test_add_from_cached_repo(
    env: Env, source_repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """When repo_dir is inside cache_dir, repo_key uses relative path."""
    cache_dir = env.home / ".cache" / "skillset" / "repos" / "owner" / "repo"
    cache_dir.mkdir(parents=True)
    for name in ("skill-a", "skill-b"):
        d = cache_dir / name
        d.mkdir()
        (d / "SKILL.md").write_text(f"# {name}\n")
    cmds = cache_dir / "commands"
    cmds.mkdir()
    (cmds / "do-thing.md").write_text("# cmd\n")

    with patch("skillset.commands._resolve.clone_or_pull", return_value=cache_dir):
        with patch("skillset.commands._resolve.get_repo_dir", return_value=cache_dir):
            with patch("skillset.commands._resolve.is_link", return_value=False):
                with patch("builtins.input", return_value="y"):
                    cmd_add(repo="owner/repo")

    output = capsys.readouterr().out
    assert "Linked" in output


def test_unsnapshot_clears_ref_and_flag(
    env: Env, source_repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """--unsnapshot drops snapshot+ref from yaml and re-links as symlinks."""
    yaml_file = env.home / ".claude" / "skillset.yaml"
    yaml_file.write_text(
        "skills:\n  owner/repo:\n    snapshot: true\n    ref: abc1234deadbeef\n    enabled: ['*']\n"
    )

    with (
        patch("skillset.commands._resolve.clone_or_pull", return_value=source_repo),
        patch("skillset.commands._resolve.get_repo_dir", return_value=source_repo),
        patch("skillset.commands._resolve.is_link", return_value=False),
    ):
        cmd_add(repo="owner/repo", skills=["skill-a"], unsnapshot=True)

    from skillset.paths import load_skillset

    entry = load_skillset(yaml_file)["skills"]["owner/repo"]
    assert "ref" not in entry
    assert "snapshot" not in entry

    skills_dir = env.home / ".claude" / "skills"
    assert (skills_dir / "skill-a").is_symlink()


def test_snapshot_and_unsnapshot_mutually_exclusive(env: Env) -> None:
    with pytest.raises(SystemExit):
        cmd_add(repo="owner/repo", snapshot=True, unsnapshot=True)
