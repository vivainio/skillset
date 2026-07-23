"""Tests for skillset.paths.get_git_root."""

import subprocess
from pathlib import Path
from unittest.mock import patch

from skillset.paths import get_git_root


def test_returns_path_in_git_repo(tmp_path: Path) -> None:
    # Initialize a real git repo
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True, check=True)
    with patch("skillset.paths.subprocess.run") as mock_run:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout=str(tmp_path) + "\n"
        )
        result = get_git_root()
        assert result == tmp_path


def test_returns_none_outside_git_repo() -> None:
    with patch(
        "skillset.paths.subprocess.run",
        side_effect=subprocess.CalledProcessError(128, "git"),
    ):
        assert get_git_root() is None


def test_returns_none_when_git_not_found() -> None:
    with patch(
        "skillset.paths.subprocess.run",
        side_effect=FileNotFoundError,
    ):
        assert get_git_root() is None
