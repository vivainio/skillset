"""Tests for skillset.commands.cmd_install_skills."""

from skillset.commands import cmd_install_skills


def test_install_skills_copies_bundled_skill(env, capsys):
    cmd_install_skills()

    skill_dir = env.home / ".claude" / "skills" / "skillset"
    assert (skill_dir / "SKILL.md").is_file()
    assert (skill_dir / ".skillset-source").is_file()
    output = capsys.readouterr().out
    assert "Installed skillset skill" in output


def test_install_skills_is_global_inside_configured_project(env, capsys, monkeypatch):
    (env.project / "skillset.yaml").write_text("skills: {}\n")
    monkeypatch.chdir(env.project)

    cmd_install_skills()

    global_skill = env.home / ".claude" / "skills" / "skillset" / "SKILL.md"
    project_skill = env.project / ".claude" / "skills" / "skillset"
    assert global_skill.is_file()
    assert not project_skill.exists()


def test_install_skills_is_idempotent(env, capsys):
    cmd_install_skills()
    capsys.readouterr()
    cmd_install_skills()

    output = capsys.readouterr().out
    assert "Installed skillset skill" in output
    skill_dir = env.home / ".claude" / "skills" / "skillset"
    assert (skill_dir / "SKILL.md").is_file()


def test_install_skills_clobbers_existing_unmanaged_dir(env, capsys):
    skills_dir = env.home / ".claude" / "skills"
    skills_dir.mkdir(parents=True)
    manual = skills_dir / "skillset"
    manual.mkdir()
    (manual / "SKILL.md").write_text("# manual\n")
    (manual / "custom-file.txt").write_text("leftover\n")

    cmd_install_skills()

    output = capsys.readouterr().out
    assert "Installed skillset skill" in output
    assert (manual / "SKILL.md").read_text() != "# manual\n"
    assert not (manual / "custom-file.txt").exists()


def test_install_skills_clobbers_existing_symlink(env, capsys, tmp_path):
    skills_dir = env.home / ".claude" / "skills"
    skills_dir.mkdir(parents=True)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    (skills_dir / "skillset").symlink_to(elsewhere)

    cmd_install_skills()

    target = skills_dir / "skillset"
    assert not target.is_symlink()
    assert (target / "SKILL.md").is_file()
