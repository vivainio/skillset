"""Tests for the durable repository storage path."""

from skillset.paths import get_cache_dir


def test_returns_data_dir_under_home(home_dir, monkeypatch):
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    assert get_cache_dir() == home_dir / ".local" / "share" / "skillset" / "repos"


def test_honors_xdg_data_home(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    assert get_cache_dir() == tmp_path / "skillset" / "repos"


def test_uses_local_appdata_on_windows(tmp_path, monkeypatch):
    monkeypatch.setattr("skillset.paths.IS_WINDOWS", True)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    assert get_cache_dir() == tmp_path / "skillset" / "repos"


def test_uses_application_support_on_macos(home_dir, monkeypatch):
    monkeypatch.setattr("skillset.paths.IS_MACOS", True)
    assert get_cache_dir() == home_dir / "Library" / "Application Support" / "skillset" / "repos"
