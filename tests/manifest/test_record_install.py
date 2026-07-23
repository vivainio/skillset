"""Tests for skillset.manifest.record_install."""

from pathlib import Path

from skillset.manifest import get_install_options, record_install


def test_basic(home_dir: Path) -> None:
    record_install("owner/repo", subpath="skills", scope="global")
    opts = get_install_options("owner/repo")
    assert opts is not None
    assert opts["subpath"] == "skills"
    assert opts["copy"] is False
    assert opts["scope"] == "global"
    assert opts["trial"] is False


def test_trial_flag(home_dir: Path) -> None:
    record_install("owner/repo", trial=True)
    opts = get_install_options("owner/repo")
    assert opts is not None
    assert opts["trial"] is True


def test_trial_preserve(home_dir: Path) -> None:
    record_install("owner/repo", trial=True)
    # Re-record without explicit trial — should preserve
    record_install("owner/repo", trial=None)
    opts = get_install_options("owner/repo")
    assert opts is not None
    assert opts["trial"] is True


def test_trial_clear(home_dir: Path) -> None:
    record_install("owner/repo", trial=True)
    record_install("owner/repo", trial=False)
    opts = get_install_options("owner/repo")
    assert opts is not None
    assert opts["trial"] is False
