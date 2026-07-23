"""Tests for skillset.paths.get_local_skillset_path."""

from pathlib import Path

import pytest

from skillset.paths import get_local_skillset_path


def test_returns_path_in_git_repo(git_root: Path) -> None:
    result = get_local_skillset_path()
    assert result == git_root / "skillset.yaml"


def test_returns_none_outside_git_repo(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("skillset.paths.get_git_root", lambda: None)
    assert get_local_skillset_path() is None
