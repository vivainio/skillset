"""Tests for skillset.linking.fuzzy_match."""

from skillset.linking import fuzzy_match


def test_exact_match() -> None:
    assert fuzzy_match("brainstorming", ["brainstorming", "other"]) == "brainstorming"


def test_close_match() -> None:
    result = fuzzy_match("brainstormin", ["brainstorming", "other"])
    assert result == "brainstorming"


def test_no_match() -> None:
    assert fuzzy_match("xyz", ["abc", "def"]) is None
