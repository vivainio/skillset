"""Tests for global cross-agent skill directory links."""

from skillset.paths import ensure_global_skills_symlinks, get_global_skills_dir


def test_links_agents_and_codex_skills_when_parents_exist(home_dir):
    target = get_global_skills_dir()
    (home_dir / ".agents").mkdir()
    (home_dir / ".codex").mkdir()

    created = ensure_global_skills_symlinks()

    expected = {home_dir / ".agents" / "skills", home_dir / ".codex" / "skills"}
    assert set(created) == expected
    assert all(path.is_symlink() and path.resolve() == target.resolve() for path in expected)


def test_skips_agent_directories_that_do_not_exist(home_dir):
    assert ensure_global_skills_symlinks() == []
    assert not (home_dir / ".agents").exists()
    assert not (home_dir / ".codex").exists()
    assert not (home_dir / ".copilot").exists()


def test_links_copilot_when_parent_exists(home_dir):
    copilot = home_dir / ".copilot"
    copilot.mkdir()

    created = ensure_global_skills_symlinks()

    assert copilot / "skills" in created
    assert (copilot / "skills").is_symlink()


def test_preserves_existing_skills_paths(home_dir):
    agents_skills = home_dir / ".agents" / "skills"
    agents_skills.mkdir(parents=True)
    marker = agents_skills / "keep"
    marker.write_text("mine")

    created = ensure_global_skills_symlinks()

    assert agents_skills not in created
    assert marker.read_text() == "mine"


def test_replaces_empty_existing_skills_directory(home_dir):
    codex_skills = home_dir / ".codex" / "skills"
    codex_skills.mkdir(parents=True)

    created = ensure_global_skills_symlinks()

    assert codex_skills in created
    assert codex_skills.is_symlink()
    assert codex_skills.resolve() == get_global_skills_dir().resolve()


def test_moves_codex_system_skills_before_linking(home_dir):
    codex_skills = home_dir / ".codex" / "skills"
    system_skills = codex_skills / ".system"
    system_skills.mkdir(parents=True)
    marker = system_skills / ".codex-system-skills.marker"
    marker.write_text("")

    created = ensure_global_skills_symlinks()

    target = get_global_skills_dir()
    assert codex_skills in created
    assert codex_skills.is_symlink()
    assert (target / ".system" / marker.name).is_file()


def test_preserves_codex_system_skills_when_destination_exists(home_dir):
    codex_system = home_dir / ".codex" / "skills" / ".system"
    codex_system.mkdir(parents=True)
    (codex_system / "source").write_text("codex")
    target_system = get_global_skills_dir() / ".system"
    target_system.mkdir(parents=True)
    (target_system / "source").write_text("claude")

    created = ensure_global_skills_symlinks()

    assert created == []
    assert (codex_system / "source").read_text() == "codex"
    assert (target_system / "source").read_text() == "claude"
