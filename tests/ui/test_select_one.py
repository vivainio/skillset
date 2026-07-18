"""Tests for the optional-fzf single-item chooser."""

from unittest.mock import patch

from skillset.ui import select_one


def test_uses_fzf_when_available():
    with (
        patch("skillset.ui.shutil.which", return_value="/usr/bin/fzf"),
        patch("skillset.ui.fzf_select", return_value=["work"]) as fzf,
    ):
        assert select_one(["work", "minimal"], prompt="Profile") == "work"
    fzf.assert_called_once_with(["work", "minimal"], prompt="Profile> ")


def test_numbered_fallback(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _prompt: "2")
    with patch("skillset.ui.shutil.which", return_value=None):
        assert select_one(["work", "minimal"]) == "minimal"


def test_empty_input_cancels_numbered_fallback(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _prompt: "")
    with patch("skillset.ui.shutil.which", return_value=None):
        assert select_one(["work"]) is None
