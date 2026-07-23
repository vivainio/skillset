"""Tests for skillset.paths.find_skillset_root."""

from pathlib import Path

import pytest

from skillset.paths import find_skillset_root


def test_finds_skillset_yaml_in_cwd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "skillset.yaml").write_text("skills: {}\n")
    monkeypatch.chdir(tmp_path)

    result = find_skillset_root()
    assert result == tmp_path


def test_finds_skillset_yaml_in_parent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "skillset.yaml").write_text("skills: {}\n")
    child = tmp_path / "sub" / "deep"
    child.mkdir(parents=True)
    monkeypatch.chdir(child)

    result = find_skillset_root()
    assert result == tmp_path


def test_returns_none_when_not_found(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = find_skillset_root()
    assert result is None
