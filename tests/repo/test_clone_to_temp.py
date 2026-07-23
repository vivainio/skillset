"""Tests for skillset.repo.clone_to_temp."""

import subprocess
from unittest.mock import patch

from skillset.repo import clone_to_temp


def test_clones_to_temp_directory() -> None:
    with patch("skillset.repo.subprocess.run") as mock_run:
        mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0)
        result = clone_to_temp("owner", "repo")

    assert result.name == "repo"
    assert result.parent.name.startswith("skillset-")
    args = mock_run.call_args[0][0]
    assert "--depth" in args
    assert "1" in args


def test_ssh_fallback_on_auth_failure() -> None:
    with patch("skillset.repo.subprocess.run") as mock_run:
        mock_run.side_effect = [
            subprocess.CalledProcessError(128, "git clone", stderr=b"Authentication failed"),
            subprocess.CompletedProcess(args=[], returncode=0),
        ]
        result = clone_to_temp("owner", "repo")

    assert result.name == "repo"
    assert mock_run.call_count == 2
    ssh_args = mock_run.call_args_list[1][0][0]
    assert "git@github.com:owner/repo.git" in ssh_args


def test_non_auth_error_raises() -> None:
    import pytest

    with patch("skillset.repo.subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.CalledProcessError(
            1, "git clone", stderr=b"network error"
        )
        with pytest.raises(subprocess.CalledProcessError):
            clone_to_temp("owner", "repo")
