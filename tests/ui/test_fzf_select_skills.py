"""Tests for skillset.ui.fzf_select_skills."""

from pathlib import Path
from unittest.mock import patch

from skillset.ui import fzf_select_skills


def _mock_fzf(*responses: list[str]) -> list[list[str]]:
    """Return a side_effect for fzf_select that yields responses in order."""
    return list(responses)


def test_single_group_flat(tmp_path: Path) -> None:
    """Skills in one group are shown flat, no drill-down."""
    repo = tmp_path / "repo"
    skills_dir = repo / "skills"
    skills = []
    for name in ("alpha", "beta"):
        d = skills_dir / name
        d.mkdir(parents=True)
        skills.append(d)

    with patch("skillset.ui.fzf_select", return_value=["  alpha"]) as mock:
        result = fzf_select_skills(skills, repo, installed=set())

    assert result == ["alpha"]
    mock.assert_called_once()
    assert mock.call_args[1]["prompt"] == "Skills> "


def test_marks_installed_skills(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    skills_dir = repo / "skills"
    skills = []
    for name in ("alpha", "beta"):
        d = skills_dir / name
        d.mkdir(parents=True)
        skills.append(d)

    with patch("skillset.ui.fzf_select", return_value=["* alpha"]) as mock:
        result = fzf_select_skills(skills, repo, installed={"alpha"})

    assert result == ["alpha"]
    # Check installed skill is marked with *
    items = mock.call_args[0][0]
    assert "* alpha" in items
    assert "  beta" in items


def test_multiple_groups_drill_down(tmp_path: Path) -> None:
    """Multiple groups: default shown flat, others as [group] entries."""
    repo = tmp_path / "repo"
    # Create two groups
    for group, names in [("skills", ["alpha"]), ("extra", ["beta"])]:
        for name in names:
            d = repo / group / name
            d.mkdir(parents=True)

    skills = [repo / "skills" / "alpha", repo / "extra" / "beta"]

    # First call: user selects [extra] group
    # Second call: user selects beta from drill-down
    with patch("skillset.ui.fzf_select", side_effect=[["[extra]"], ["  beta"]]):
        result = fzf_select_skills(skills, repo, installed=set())

    assert result == ["beta"]


def test_mixed_selection_flat_and_group(tmp_path: Path) -> None:
    """User selects both flat items and drills into a group."""
    repo = tmp_path / "repo"
    for group, names in [("skills", ["alpha"]), ("extra", ["beta", "gamma"])]:
        for name in names:
            d = repo / group / name
            d.mkdir(parents=True)

    skills = [repo / "skills" / "alpha", repo / "extra" / "beta", repo / "extra" / "gamma"]

    # User selects alpha (flat) and [extra] group, then selects gamma from extra
    with patch("skillset.ui.fzf_select", side_effect=[["  alpha", "[extra]"], ["  gamma"]]):
        result = fzf_select_skills(skills, repo, installed=set())

    assert "alpha" in result
    assert "gamma" in result
    assert "beta" not in result


def test_empty_skills_returns_empty(tmp_path: Path) -> None:
    repo = tmp_path / "repo"

    with patch("skillset.ui.fzf_select", return_value=[]):
        result = fzf_select_skills([], repo, installed=set())

    assert result == []
