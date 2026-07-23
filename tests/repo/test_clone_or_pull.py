"""Tests for skillset.repo.clone_or_pull."""

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from skillset.repo import clone_or_pull


def test_clones_new_repo(home_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    with patch("skillset.repo.subprocess.run") as mock_run:
        mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0)
        result = clone_or_pull("owner", "repo")

    expected = home_dir / ".local" / "share" / "skillset" / "repos" / "owner" / "repo"
    assert result == expected
    assert mock_run.call_count == 1
    args = mock_run.call_args[0][0]
    assert args[0] == "git"
    assert args[1] == "clone"
    assert "https://github.com/owner/repo.git" in args


def test_pulls_existing_repo(home_dir: Path) -> None:
    repo_dir = home_dir / ".cache" / "skillset" / "repos" / "owner" / "repo"
    repo_dir.mkdir(parents=True)

    with patch("skillset.repo.subprocess.run") as mock_run:
        mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0)
        result = clone_or_pull("owner", "repo")

    assert result == repo_dir
    args = mock_run.call_args[0][0]
    assert args == ["git", "pull"]


def test_pull_failure_warns(home_dir: Path, capsys: pytest.CaptureFixture[str]) -> None:
    repo_dir = home_dir / ".cache" / "skillset" / "repos" / "owner" / "repo"
    repo_dir.mkdir(parents=True)

    with patch("skillset.repo.subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.CalledProcessError(
            1, "git pull", stderr=b"merge conflict"
        )
        result = clone_or_pull("owner", "repo")

    assert result == repo_dir
    output = capsys.readouterr().out
    assert "Warning" in output


def test_clone_ssh_fallback(home_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    with patch("skillset.repo.subprocess.run") as mock_run:
        # First call (HTTPS) fails with auth error, second (SSH) succeeds
        mock_run.side_effect = [
            subprocess.CalledProcessError(128, "git clone", stderr=b"Authentication failed"),
            subprocess.CompletedProcess(args=[], returncode=0),
        ]
        result = clone_or_pull("owner", "repo")

    expected = home_dir / ".local" / "share" / "skillset" / "repos" / "owner" / "repo"
    assert result == expected
    assert mock_run.call_count == 2
    # Second call should use SSH URL
    ssh_args = mock_run.call_args_list[1][0][0]
    assert "git@github.com:owner/repo.git" in ssh_args


def test_clone_non_auth_error_raises(home_dir: Path) -> None:
    import pytest

    with patch("skillset.repo.subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.CalledProcessError(
            1, "git clone", stderr=b"some other error"
        )
        with pytest.raises(subprocess.CalledProcessError):
            clone_or_pull("owner", "repo")
