"""Tests for skillset.paths.require_project_dir."""

from pathlib import Path

import pytest

from skillset.paths import require_project_dir


def test_returns_path_when_given() -> None:
    p = Path("/some/path")
    assert require_project_dir(p) is p


def test_exits_on_none() -> None:
    with pytest.raises(SystemExit):
        require_project_dir(None)
