"""Skill, command, and agent discovery in repositories."""

from pathlib import Path

from ruamel.yaml import YAML

_frontmatter_yaml = YAML(typ="safe")


def parse_skill_metadata(skill_dir: Path) -> tuple[str, str]:
    """Parse (name, description) from a skill's SKILL.md frontmatter.

    Falls back to the directory name and an empty description if the
    frontmatter is missing or malformed.
    """
    name = skill_dir.name
    description = ""
    try:
        text = (skill_dir / "SKILL.md").read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return name, description
    if not text.startswith("---"):
        return name, description
    end = text.find("\n---", 3)
    if end == -1:
        return name, description
    try:
        data = _frontmatter_yaml.load(text[3:end])
    except Exception:
        return name, description
    if isinstance(data, dict):
        name = str(data.get("name") or name)
        description = str(data.get("description") or "")
    return name, description


def find_skills(repo_dir: Path) -> list[Path]:
    """Find skill directories in a repo. A skill is a dir containing SKILL.md."""
    skills = []
    for skill_file in repo_dir.glob("**/SKILL.md"):
        if any(part.startswith(".") for part in skill_file.relative_to(repo_dir).parts):
            continue
        skill_dir = skill_file.parent
        if skill_dir not in skills:
            skills.append(skill_dir)
    return skills


def find_commands(repo_dir: Path) -> list[Path]:
    """Find command files in a repo. Commands are .md files in commands/ directories (nested ok)."""
    commands = []
    for cmd_file in repo_dir.glob("**/commands/**/*.md"):
        if any(part.startswith(".") for part in cmd_file.relative_to(repo_dir).parts):
            continue
        commands.append(cmd_file)
    # Also check direct children of commands/
    for cmd_file in repo_dir.glob("**/commands/*.md"):
        if any(part.startswith(".") for part in cmd_file.relative_to(repo_dir).parts):
            continue
        if cmd_file not in commands:
            commands.append(cmd_file)
    return commands


def find_agents(repo_dir: Path) -> list[tuple[Path, Path]]:
    """Find Claude agent files, returning ``(source, install-relative path)``.

    Agents are Markdown files below any directory named ``agents``. Unlike the
    other hidden directories, ``.claude/agents`` is an intentional canonical
    source and is included. If *repo_dir* is itself named ``agents``, it is
    treated as the agent root; this makes ``-p path/to/agents`` useful.
    """
    roots = [repo_dir] if repo_dir.name == "agents" else []
    roots.extend(
        path
        for path in repo_dir.glob("**/agents")
        if path.is_dir()
        and not any(
            part.startswith(".") and part != ".claude" for part in path.relative_to(repo_dir).parts
        )
    )
    agents: list[tuple[Path, Path]] = []
    seen: set[Path] = set()
    for root in roots:
        for agent_file in root.rglob("*.md"):
            relative = agent_file.relative_to(root)
            if any(part.startswith(".") for part in relative.parts):
                continue
            if agent_file not in seen:
                agents.append((agent_file, relative))
                seen.add(agent_file)
    return agents
