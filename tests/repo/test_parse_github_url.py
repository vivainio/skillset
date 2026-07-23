"""Tests for skillset.repo.parse_github_url."""

from skillset.repo import parse_github_url


def test_simple_url() -> None:
    result = parse_github_url("https://github.com/owner/repo")
    assert result == ("owner", "repo", None, None)


def test_with_tree() -> None:
    result = parse_github_url("https://github.com/owner/repo/tree/main/skills")
    assert result == ("owner", "repo", "main", "skills")


def test_deep_path() -> None:
    result = parse_github_url("https://github.com/owner/repo/tree/main/a/b/c")
    assert result == ("owner", "repo", "main", "a/b/c")


def test_strips_git_suffix() -> None:
    result = parse_github_url("https://github.com/owner/repo.git")
    assert result == ("owner", "repo", None, None)


def test_trailing_slash() -> None:
    result = parse_github_url("https://github.com/owner/repo/")
    assert result == ("owner", "repo", None, None)


def test_rejects_non_github() -> None:
    assert parse_github_url("https://gitlab.com/owner/repo") is None


def test_rejects_non_url() -> None:
    assert parse_github_url("owner/repo") is None
