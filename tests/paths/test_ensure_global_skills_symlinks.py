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
