"""Tests for skillset.repo.parse_repo_spec."""

import pytest

from skillset.repo import parse_repo_spec


def test_valid() -> None:
    assert parse_repo_spec("owner/repo") == ("owner", "repo")


def test_strips_whitespace() -> None:
    assert parse_repo_spec("  owner/repo  ") == ("owner", "repo")


def test_rejects_single_name() -> None:
    with pytest.raises(ValueError, match="Invalid repo format"):
        parse_repo_spec("just-a-name")


def test_rejects_too_many_parts() -> None:
    with pytest.raises(ValueError, match="Invalid repo format"):
        parse_repo_spec("a/b/c")
