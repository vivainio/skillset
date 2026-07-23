"""Tests for saving and activating global skill profiles."""

from pathlib import Path

from skillset.linking import copy_dir, create_dir_link
from skillset.paths import get_global_skills_dir, get_profile_store_dir
from skillset.profiles import (
    activate_profile,
    active_profile,
    delete_profile,
    profile_names,
    save_profile,
)


def _skill(path: Path) -> Path:
    path.mkdir(parents=True)
    (path / "SKILL.md").write_text(f"# {path.name}\n")
    return path


def test_save_and_switch_managed_skills(home_dir: Path, tmp_path: Path) -> None:
    sources = tmp_path / "sources"
    alpha = _skill(sources / "alpha")
    beta = _skill(sources / "beta")
    installed = get_global_skills_dir()
    installed.mkdir(parents=True)
    create_dir_link(installed / "alpha", alpha)

    assert save_profile("minimal") == (1, [])

    create_dir_link(installed / "beta", beta)
    assert save_profile("full") == (2, [])

    activated, removed = activate_profile("minimal")

    assert (activated, removed) == (1, 1)
    assert (installed / "alpha").resolve() == alpha
    assert not (installed / "beta").exists()
    assert active_profile() == "minimal"


def test_save_leaves_unmanaged_skill_alone_by_default(home_dir: Path) -> None:
    unmanaged = _skill(get_global_skills_dir() / "personal")

    count, skipped = save_profile("work")

    assert count == 0
    assert skipped == ["personal"]
    assert unmanaged.is_dir()
    assert not unmanaged.is_symlink()


def test_save_can_adopt_unmanaged_skill(home_dir: Path) -> None:
    original = _skill(get_global_skills_dir() / "personal")

    count, skipped = save_profile("work", include_unmanaged=True)

    stored = get_profile_store_dir() / "personal"
    assert (count, skipped) == (1, [])
    assert original.is_symlink()
    assert original.resolve() == stored
    assert (stored / "SKILL.md").is_file()


def test_save_stores_managed_copy_so_it_can_be_reactivated(home_dir: Path, tmp_path: Path) -> None:
    source = _skill(tmp_path / "source")
    installed = get_global_skills_dir()
    installed.mkdir(parents=True)
    copy_dir(source, installed / "snapshot", source_label="owner/repo")

    save_profile("snapshot")

    stored = get_profile_store_dir() / "snapshot"
    assert (installed / "snapshot").is_symlink()
    assert (installed / "snapshot").resolve() == stored


def test_switch_does_not_touch_unrelated_unmanaged_skill(home_dir: Path, tmp_path: Path) -> None:
    source = _skill(tmp_path / "managed")
    installed = get_global_skills_dir()
    installed.mkdir(parents=True)
    create_dir_link(installed / "managed", source)
    save_profile("with-managed")
    personal = _skill(installed / "personal")
    save_profile("without-managed")

    activate_profile("with-managed")

    assert personal.is_dir()
    assert not personal.is_symlink()


def test_delete_keeps_stored_skill(home_dir: Path) -> None:
    _skill(get_global_skills_dir() / "personal")
    save_profile("work", include_unmanaged=True)
    stored = get_profile_store_dir() / "personal"

    delete_profile("work")

    assert stored.is_dir()
    assert profile_names() == []
    assert active_profile() is None
