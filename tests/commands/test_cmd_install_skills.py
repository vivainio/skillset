"""Tests for skillset.commands.cmd_install_skills."""

from skillset.commands import cmd_install_skills


def test_install_skills_copies_bundled_skill(env, capsys):
    cmd_install_skills()

    skill_dir = env.home / ".claude" / "skills" / "skillset"
    assert (skill_dir / "SKILL.md").is_file()
    assert (skill_dir / ".skillset-source").is_file()
    output = capsys.readouterr().out
    assert "Installed skillset skill" in output


def test_install_skills_is_idempotent(env, capsys):
    cmd_install_skills()
    capsys.readouterr()
    cmd_install_skills()

    output = capsys.readouterr().out
    assert "Installed skillset skill" in output
    skill_dir = env.home / ".claude" / "skills" / "skillset"
    assert (skill_dir / "SKILL.md").is_file()


def test_install_skills_skips_unmanaged_existing_dir(env, capsys):
    skills_dir = env.home / ".claude" / "skills"
    skills_dir.mkdir(parents=True)
    manual = skills_dir / "skillset"
    manual.mkdir()
    (manual / "SKILL.md").write_text("# manual\n")

    cmd_install_skills()

    output = capsys.readouterr().out
    assert "already exists" in output
    assert (manual / "SKILL.md").read_text() == "# manual\n"
