"""Tests for duplicate cached/editable repository repair."""

import subprocess
from unittest.mock import patch

from skillset.commands.update_repair import (
    remove_redundant_cached_repos,
    report_or_repair_duplicate_sources,
)
from skillset.paths import load_skillset


def _git_repo(path, remote):
    path.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=path, check=True)
    subprocess.run(["git", "remote", "add", "origin", remote], cwd=path, check=True)
    return path


def _skill(root, name):
    path = root / "skills" / name
    path.mkdir(parents=True)
    (path / "SKILL.md").write_text(f"# {name}\n")


def test_reports_cached_and_editable_duplicate(tmp_path, capsys):
    checkout = _git_repo(tmp_path / "checkout", "git@github.com:owner/repo.git")
    config_path = tmp_path / "skillset.yaml"
    config = {
        "skills": {
            "owner/repo": {"enabled": ["one"]},
            "local": {"editable": True, "source": str(checkout), "enabled": ["*"]},
        }
    }

    changed = report_or_repair_duplicate_sources(config, config_path)

    assert changed is False
    output = capsys.readouterr().out
    assert "owner/repo: cached and editable via local" in output
    assert "skillset update --repair" in output


def test_repair_consolidates_enabled_union_under_repo_key(tmp_path):
    checkout = _git_repo(tmp_path / "checkout", "https://github.com/owner/repo.git")
    _skill(checkout, "one")
    _skill(checkout, "two")
    config_path = tmp_path / "skillset.yaml"
    config = {
        "skills": {
            "owner/repo": {"path": "skills", "enabled": ["one"]},
            "local": {
                "editable": True,
                "source": str(checkout / "skills"),
                "enabled": ["two"],
            },
        }
    }

    changed = report_or_repair_duplicate_sources(config, config_path, repair=True)

    assert changed is True
    repaired = load_skillset(config_path)["skills"]
    assert list(repaired) == ["owner/repo"]
    assert repaired["owner/repo"]["editable"] is True
    assert repaired["owner/repo"]["source"] == str(checkout)
    assert repaired["owner/repo"]["enabled"] == ["one", "two"]


def test_repair_refuses_conflicting_copy_modes(tmp_path, capsys):
    checkout = _git_repo(tmp_path / "checkout", "git@github.com:owner/repo.git")
    config_path = tmp_path / "skillset.yaml"
    config = {
        "skills": {
            "owner/repo": {"enabled": ["one"], "copy": True},
            "local": {"editable": True, "source": str(checkout), "enabled": ["one"]},
        }
    }

    changed = report_or_repair_duplicate_sources(config, config_path, repair=True)

    assert changed is False
    assert "conflicting copy settings" in capsys.readouterr().out
    assert not config_path.exists()


def test_repair_removes_missing_editable_source(tmp_path, capsys):
    config_path = tmp_path / "skillset.yaml"
    config = {
        "skills": {
            "missing": {
                "editable": True,
                "source": str(tmp_path / "gone"),
                "enabled": ["*"],
            },
            "valid": {
                "editable": True,
                "source": str(tmp_path),
                "enabled": ["*"],
            },
        }
    }

    changed = report_or_repair_duplicate_sources(config, config_path, repair=True)

    assert changed is True
    assert list(load_skillset(config_path)["skills"]) == ["valid"]
    assert "Removed missing: source not found" in capsys.readouterr().out


def test_repair_records_cache_candidate_only_after_safe_consolidation(home_dir, tmp_path):
    checkout = _git_repo(tmp_path / "checkout", "git@github.com:owner/repo.git")
    (home_dir / ".cache" / "skillset" / "repos" / "owner" / "repo").mkdir(parents=True)
    config_path = tmp_path / "skillset.yaml"
    config = {
        "skills": {
            "owner/repo": {"enabled": ["one"]},
            "local": {"editable": True, "source": str(checkout), "enabled": ["one"]},
        }
    }
    candidates = []

    report_or_repair_duplicate_sources(
        config, config_path, repair=True, purge_candidates=candidates
    )

    assert candidates == [("owner/repo", checkout)]


def test_repair_finds_cache_for_editable_only_entry(home_dir, tmp_path):
    checkout = _git_repo(tmp_path / "checkout", "git@github.com:owner/repo.git")
    (home_dir / ".cache" / "skillset" / "repos" / "owner" / "repo").mkdir(parents=True)
    config_path = tmp_path / "skillset.yaml"
    config = {
        "skills": {
            "owner/repo": {
                "editable": True,
                "source": str(checkout),
                "enabled": ["one"],
            }
        }
    }
    candidates = []

    changed = report_or_repair_duplicate_sources(
        config, config_path, repair=True, purge_candidates=candidates
    )

    assert changed is False
    assert candidates == [("owner/repo", checkout)]


def test_repair_deduplicates_cache_candidates_for_editable_aliases(home_dir, tmp_path):
    checkout = _git_repo(tmp_path / "checkout", "git@github.com:owner/repo.git")
    (home_dir / ".cache" / "skillset" / "repos" / "owner" / "repo").mkdir(parents=True)
    config_path = tmp_path / "skillset.yaml"
    config = {
        "skills": {
            "first": {"editable": True, "source": str(checkout), "enabled": ["one"]},
            "second": {"editable": True, "source": str(checkout), "enabled": ["two"]},
        }
    }
    candidates = []

    report_or_repair_duplicate_sources(
        config, config_path, repair=True, purge_candidates=candidates
    )

    assert candidates == [("owner/repo", checkout)]


def test_removes_redundant_cache_when_confirmed(home_dir, tmp_path, capsys):
    cache = home_dir / ".cache" / "skillset" / "repos" / "owner" / "repo"
    cache.mkdir(parents=True)
    (cache / "file").write_text("cached")

    with patch("builtins.input", return_value=""):
        remove_redundant_cached_repos([("owner/repo", tmp_path / "checkout")])

    assert not cache.exists()
    assert not cache.parent.exists()
    assert "Removed cached clone" in capsys.readouterr().out


def test_keeps_redundant_cache_when_declined(home_dir, tmp_path, capsys):
    cache = home_dir / ".cache" / "skillset" / "repos" / "owner" / "repo"
    cache.mkdir(parents=True)

    with patch("builtins.input", return_value="n"):
        remove_redundant_cached_repos([("owner/repo", tmp_path / "checkout")])

    assert cache.exists()
    assert "Kept cached clone" in capsys.readouterr().out


def test_yes_removes_without_prompt(home_dir, tmp_path):
    cache = home_dir / ".cache" / "skillset" / "repos" / "owner" / "repo"
    cache.mkdir(parents=True)

    with patch("builtins.input") as prompt:
        remove_redundant_cached_repos([("owner/repo", tmp_path / "checkout")], answer="yes")

    prompt.assert_not_called()
    assert not cache.exists()


def test_no_reports_cache_without_prompt(home_dir, tmp_path, capsys):
    cache = home_dir / ".cache" / "skillset" / "repos" / "owner" / "repo"
    cache.mkdir(parents=True)

    with patch("builtins.input") as prompt:
        remove_redundant_cached_repos([("owner/repo", tmp_path / "checkout")], answer="no")

    prompt.assert_not_called()
    assert cache.exists()
    assert "Redundant cached clone remains" in capsys.readouterr().out
