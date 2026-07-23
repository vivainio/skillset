"""Tests for skillset.ui.is_local_path."""

from skillset.ui import is_local_path


def test_absolute_path() -> None:
    assert is_local_path("/some/path") is True


def test_relative_path() -> None:
    assert is_local_path("./local") is True


def test_home_path() -> None:
    assert is_local_path("~/skills") is True


def test_owner_repo_format() -> None:
    assert is_local_path("owner/repo") is False
