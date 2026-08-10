from pathlib import Path

from skillset.linking import link_agents


def test_links_agents_and_preserves_nested_paths(tmp_path: Path) -> None:
    source = tmp_path / "source"
    agents = source / "package" / "agents" / "review"
    agents.mkdir(parents=True)
    agent = agents / "security.md"
    agent.write_text("# security\n")
    target = tmp_path / "target"

    assert link_agents(source, target) == ["review/security"]
    assert (target / "review" / "security.md").resolve() == agent


def test_skips_colliding_relative_agent_paths(tmp_path: Path, capsys) -> None:
    source = tmp_path / "source"
    for package in ("one", "two"):
        root = source / package / "agents"
        root.mkdir(parents=True)
        (root / "reviewer.md").write_text(f"# {package}\n")

    assert link_agents(source, tmp_path / "target") == []
    assert "conflicting agent path(s): reviewer.md" in capsys.readouterr().out


def test_filters_agents_by_relative_name(tmp_path: Path) -> None:
    source = tmp_path / "source"
    root = source / "agents"
    root.mkdir(parents=True)
    for name in ("reviewer", "tester"):
        (root / f"{name}.md").write_text(f"# {name}\n")

    target = tmp_path / "target"
    assert link_agents(source, target, only={"reviewer"}) == ["reviewer"]
    assert (target / "reviewer.md").is_symlink()
    assert not (target / "tester.md").exists()
