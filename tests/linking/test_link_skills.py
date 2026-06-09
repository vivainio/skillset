"""Tests for skillset.linking.link_skills."""

from skillset.linking import copy_dir, is_managed_copy, link_skills


def test_copy_mode(skill_repo, tmp_path):
    target = tmp_path / "skills"
    linked = link_skills(skill_repo, target, copy=True)
    assert sorted(linked) == ["skill-a", "skill-b"]
    assert (target / "skill-a" / "SKILL.md").exists()
    assert is_managed_copy(target / "skill-a")


def test_symlink_mode(skill_repo, tmp_path):
    target = tmp_path / "skills"
    linked = link_skills(skill_repo, target)
    assert sorted(linked) == ["skill-a", "skill-b"]
    assert (target / "skill-a").is_symlink()


def test_with_filter(skill_repo, tmp_path):
    target = tmp_path / "skills"
    linked = link_skills(skill_repo, target, only={"skill-a"}, copy=True)
    assert linked == ["skill-a"]
    assert not (target / "skill-b").exists()


def test_glob_filter(skill_repo, tmp_path):
    target = tmp_path / "skills"
    linked = link_skills(skill_repo, target, only={"skill-*"}, copy=True)
    assert sorted(linked) == ["skill-a", "skill-b"]


def test_percent_wildcard_alias(skill_repo, tmp_path):
    """`%` is accepted as a shell-safe alias for `*`."""
    target = tmp_path / "skills"
    linked = link_skills(skill_repo, target, only={"skill-%"}, copy=True)
    assert sorted(linked) == ["skill-a", "skill-b"]


def test_existing_only(skill_repo, tmp_path):
    target = tmp_path / "skills"
    target.mkdir(parents=True)
    copy_dir(skill_repo / "skill-a", target / "skill-a")

    linked = link_skills(skill_repo, target, existing_only=True, copy=True)
    assert linked == ["skill-a"]


def test_subfolder_target(skill_repo, tmp_path):
    """Skills are installed into a subfolder when target_dir includes it."""
    target = tmp_path / "skills" / "database"
    linked = link_skills(skill_repo, target, copy=True)
    assert sorted(linked) == ["skill-a", "skill-b"]
    assert (target / "skill-a" / "SKILL.md").exists()
    assert (target / "skill-b" / "SKILL.md").exists()
    assert target.parent.exists()


def test_replaces_existing_managed(skill_repo, tmp_path):
    target = tmp_path / "skills"
    # First install as copy
    link_skills(skill_repo, target, copy=True)
    # Re-install replaces existing managed entries
    linked = link_skills(skill_repo, target, copy=True)
    assert sorted(linked) == ["skill-a", "skill-b"]


def test_skips_unmanaged_existing(skill_repo, tmp_path, capsys):
    target = tmp_path / "skills"
    target.mkdir(parents=True)
    # Create a non-managed dir with same name
    manual = target / "skill-a"
    manual.mkdir()
    (manual / "README.md").write_text("manual")

    linked = link_skills(skill_repo, target, copy=True)
    assert "skill-a" not in linked
    assert "skill-b" in linked
    output = capsys.readouterr().out
    assert "not managed by skillset" in output


def test_fuzzy_match_suggestion(skill_repo, tmp_path, capsys):
    target = tmp_path / "skills"
    link_skills(skill_repo, target, only={"skill-"}, copy=True)
    # "skill-" doesn't exactly match or glob-match, fuzzy should suggest
    output = capsys.readouterr().out
    assert "not found" in output


def test_no_match_no_suggestion(skill_repo, tmp_path, capsys):
    target = tmp_path / "skills"
    linked = link_skills(skill_repo, target, only={"zzzzz"}, copy=True)
    assert linked == []
    output = capsys.readouterr().out
    assert "no close match" in output


def test_glob_no_match(skill_repo, tmp_path, capsys):
    target = tmp_path / "skills"
    linked = link_skills(skill_repo, target, only={"zzz-*"}, copy=True)
    assert linked == []
    output = capsys.readouterr().out
    assert "matched no skills" in output


def test_source_label(skill_repo, tmp_path):
    target = tmp_path / "skills"
    link_skills(skill_repo, target, copy=True, source_label="custom/label")
    from skillset.linking import get_copy_source

    assert get_copy_source(target / "skill-a") == "custom/label"


def test_existing_only_with_only_set(skill_repo, tmp_path):
    """existing_only intersects with the explicit only set."""
    target = tmp_path / "skills"
    target.mkdir(parents=True)
    # Only skill-a exists in target
    copy_dir(skill_repo / "skill-a", target / "skill-a")

    # Request both, but existing_only should restrict to just skill-a
    linked = link_skills(
        skill_repo, target, only={"skill-a", "skill-b"}, existing_only=True, copy=True
    )
    assert linked == ["skill-a"]
    assert not (target / "skill-b").exists()
