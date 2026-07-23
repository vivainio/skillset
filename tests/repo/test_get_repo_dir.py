"""Tests for skillset.repo.get_repo_dir."""

from pathlib import Path

import pytest

from skillset.repo import get_repo_dir


def test_returns_path_under_data_dir(home_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    result = get_repo_dir("owner", "repo")
    assert result == home_dir / ".local" / "share" / "skillset" / "repos" / "owner" / "repo"


def test_returns_existing_legacy_repo(home_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    legacy = home_dir / ".cache" / "skillset" / "repos" / "owner" / "repo"
    legacy.mkdir(parents=True)

    assert get_repo_dir("owner", "repo") == legacy
