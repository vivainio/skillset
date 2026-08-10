from pathlib import Path

from skillset.discovery import find_agents


def test_finds_agents_anywhere_and_preserves_relative_path(tmp_path: Path) -> None:
    nested = tmp_path / "package" / "agents" / "review"
    nested.mkdir(parents=True)
    agent = nested / "security.md"
    agent.write_text("---\nname: security\n---\n")

    assert find_agents(tmp_path) == [(agent, Path("review/security.md"))]


def test_finds_canonical_hidden_claude_agents(tmp_path: Path) -> None:
    root = tmp_path / ".claude" / "agents"
    root.mkdir(parents=True)
    agent = root / "reviewer.md"
    agent.write_text("# reviewer\n")

    assert find_agents(tmp_path) == [(agent, Path("reviewer.md"))]


def test_path_can_be_agents_root(tmp_path: Path) -> None:
    root = tmp_path / "agents"
    root.mkdir()
    agent = root / "reviewer.md"
    agent.write_text("# reviewer\n")

    assert find_agents(root) == [(agent, Path("reviewer.md"))]


def test_ignores_unrelated_markdown_and_hidden_roots(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# docs\n")
    hidden = tmp_path / ".hidden" / "agents"
    hidden.mkdir(parents=True)
    (hidden / "secret.md").write_text("# secret\n")

    assert find_agents(tmp_path) == []
