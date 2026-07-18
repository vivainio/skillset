"""Tests for skillset.ui.fzf_select."""

import subprocess
from unittest.mock import patch

import pytest

from skillset.ui import fzf_select


def _make_fzf_result(stdout: str, returncode: int = 0):
    return subprocess.CompletedProcess(args=["fzf"], returncode=returncode, stdout=stdout)


def test_returns_selected_items():
    with patch("skillset.ui.subprocess.run", return_value=_make_fzf_result("alpha\nbeta\n")):
        result = fzf_select(["alpha", "beta", "gamma"], prompt="Test> ")

    assert result == ["alpha", "beta"]


def test_empty_selection_returns_empty():
    with patch("skillset.ui.subprocess.run", return_value=_make_fzf_result("", returncode=1)):
        result = fzf_select(["a", "b"])

    assert result == []


def test_fzf_failure_exits(capsys):
    with patch("skillset.ui.subprocess.run", return_value=_make_fzf_result("", returncode=2)):
        with pytest.raises(SystemExit):
            fzf_select(["a"])

    assert "fzf not found or failed" in capsys.readouterr().err


def test_passes_items_and_prompt():
    with patch("skillset.ui.subprocess.run", return_value=_make_fzf_result("x\n")) as mock_run:
        fzf_select(["x", "y"], prompt="Pick> ")

    call_args = mock_run.call_args
    assert call_args[1]["input"] == "x\ny"
    assert "--prompt" in call_args[0][0]
    assert "Pick> " in call_args[0][0]


def test_preserve_order_disables_fzf_sorting():
    with patch("skillset.ui.subprocess.run", return_value=_make_fzf_result("")) as mock_run:
        fzf_select(["# source", "  skill"], preserve_order=True)

    assert "--no-sort" in mock_run.call_args[0][0]


def test_strips_empty_lines():
    with patch("skillset.ui.subprocess.run", return_value=_make_fzf_result("\nalpha\n\nbeta\n\n")):
        result = fzf_select(["alpha", "beta"])

    assert result == ["alpha", "beta"]
