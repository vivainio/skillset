"""Command handler for printing a skill's SKILL.md without installing it."""

import sys
from pathlib import Path

from skillset.commands.search import iter_matching_skills
from skillset.paths import abbrev

_MAX_RESOURCES = 200


def _pick_skill(query: list[str]) -> tuple[str, Path, str]:
    """Return (source_key, skill_dir, name) for the single best match, or exit."""
    matches = list(iter_matching_skills(query))
    if not matches:
        print("No matching skills found", file=sys.stderr)
        sys.exit(1)
    if len(matches) > 1:
        exact = [m for m in matches if m[2].lower() == " ".join(query).lower()]
        if len(exact) == 1:
            matches = exact
    if len(matches) > 1:
        print(f"{len(matches)} skills match -- be more specific:", file=sys.stderr)
        for key, skill_dir, name, _desc in sorted(matches, key=lambda m: (m[0], m[2])):
            print(f"  {name}  [{key}]  {abbrev(skill_dir)}", file=sys.stderr)
        sys.exit(1)
    key, skill_dir, name, _desc = matches[0]
    return key, skill_dir, name


def _nested_resources(skill_dir: Path) -> list[Path]:
    """Files under the skill dir other than its SKILL.md (hidden entries skipped)."""
    files = []
    for path in sorted(skill_dir.rglob("*")):
        rel = path.relative_to(skill_dir)
        if not path.is_file() or rel == Path("SKILL.md"):
            continue
        if any(part.startswith(".") for part in rel.parts):
            continue
        files.append(path)
    return files


def cmd_get(query: list[str]) -> None:
    """Print a skill's SKILL.md plus absolute paths to its nested resources."""
    key, skill_dir, name = _pick_skill(query)
    skill_dir = skill_dir.resolve()
    content = (skill_dir / "SKILL.md").read_text(encoding="utf-8", errors="replace")

    print(f"# Skill: {name}  [{key}]")
    print(f"# Directory: {abbrev(skill_dir)}")
    print("# Relative paths in the SKILL.md below are relative to that directory.")
    print()
    print(content.rstrip())

    resources = _nested_resources(skill_dir)
    if not resources:
        return
    print("\n# Resources")
    for path in resources[:_MAX_RESOURCES]:
        print(abbrev(path))
    if len(resources) > _MAX_RESOURCES:
        print(f"... and {len(resources) - _MAX_RESOURCES} more under {abbrev(skill_dir)}")
