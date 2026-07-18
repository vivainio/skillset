"""Tests for skillset.commands.cmd_search."""

from skillset.commands import cmd_search
from skillset.paths import save_skillset


def _cache_repo(env, owner, name, skills):
    """Create a fake cached repo with the given skill_name -> description map."""
    repo_dir = env.home / ".cache" / "skillset" / "repos" / owner / name
    for skill_name, description in skills.items():
        skill_dir = repo_dir / skill_name
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            f"---\nname: {skill_name}\ndescription: {description}\n---\n# {skill_name}\n"
        )
    return repo_dir


def test_search_no_sources(env, capsys):
    cmd_search(query=["jira"])
    output = capsys.readouterr().out
    assert "No matching skills found" in output


def test_search_matches_description(env, capsys):
    _cache_repo(env, "owner", "repo", {"zaira": "Access Jira tickets offline"})

    cmd_search(query=["jira"])
    output = capsys.readouterr().out
    assert "owner/repo" in output
    assert "zaira" in output
    assert "1 skill(s) found" in output


def test_search_matches_name(env, capsys):
    _cache_repo(env, "owner", "repo", {"jira-check": "Pre-release checklist"})

    cmd_search(query=["jira"])
    output = capsys.readouterr().out
    assert "jira-check" in output


def test_search_requires_all_terms(env, capsys):
    _cache_repo(env, "owner", "repo", {"zaira": "Access Jira tickets offline"})

    cmd_search(query=["jira", "nomatch"])
    output = capsys.readouterr().out
    assert "No matching skills found" in output


def test_search_glob_prefix(env, capsys):
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


def test_search_glob_percent_alias(env, capsys):
    _cache_repo(env, "owner", "repo", {"jira-check": "Pre-release checklist"})

    cmd_search(query=["jira-%"])
    output = capsys.readouterr().out
    assert "jira-check" in output


def test_search_glob_substring(env, capsys):
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


def test_search_skips_local_alias_dir(env, capsys):
    """The repos/local/ dir is for editable-source symlinks -- not scanned directly."""
    _cache_repo(env, "local", "some-repo", {"zaira": "Access Jira tickets offline"})

    cmd_search(query=["jira"])
    output = capsys.readouterr().out
    assert "No matching skills found" in output


def test_search_editable_source(env, capsys, tmp_path):
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


def test_search_installed_unmanaged_skill(env, capsys):
    skill_dir = env.home / ".claude" / "skills" / "personal"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: personal\ndescription: Personal Jira workflow\n---\n"
    )

    cmd_search(query=["jira"])

    output = capsys.readouterr().out
    assert "Unmanaged:" in output
    assert "personal" in output


def test_search_saved_unmanaged_skill(env, capsys):
    skill_dir = env.home / ".claude" / ".skillset" / "skills" / "personal"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: personal\ndescription: Personal Jira workflow\n---\n"
    )

    cmd_search(query=["jira"])

    output = capsys.readouterr().out
    assert "Saved unmanaged:" in output
    assert "personal" in output
