"""Tests for skillset.ui.register_local_lib."""

from skillset.ui import register_local_lib


def test_creates_symlink_in_cache(home_dir, tmp_path):
    source = tmp_path / "my-skills"
    source.mkdir()

    register_local_lib(source)

    link = home_dir / ".local" / "share" / "skillset" / "repos" / "local" / "my-skills"
    assert link.is_symlink()
    assert link.resolve() == source.resolve()


def test_replaces_existing_link(home_dir, tmp_path):
    source1 = tmp_path / "v1"
    source1.mkdir()
    source2 = tmp_path / "v2"
    source2.mkdir()

    # Register with a name that would collide
    # Use source2 with same dir name
    local_dir = home_dir / ".local" / "share" / "skillset" / "repos" / "local"
    local_dir.mkdir(parents=True)
    link = local_dir / "v1"
    link.symlink_to(source2)

    register_local_lib(source1)
    assert link.resolve() == source1.resolve()


def test_skips_non_link_existing(home_dir, tmp_path):
    source = tmp_path / "skills"
    source.mkdir()

    local_dir = home_dir / ".cache" / "skillset" / "repos" / "local"
    local_dir.mkdir(parents=True)
    existing = local_dir / "skills"
    existing.mkdir()  # regular dir, not a link

    register_local_lib(source)
    # Should NOT replace the regular dir
    assert not existing.is_symlink()
