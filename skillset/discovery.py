"""Skill and command discovery — find SKILL.md and commands/ in repos."""

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
