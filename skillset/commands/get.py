"""Command handler for printing a skill's SKILL.md without installing it."""

import sys
from pathlib import Path

from skillset.commands.search import iter_matching_skills
from skillset.linking import has_glob, is_link
from skillset.manifest import record_install
from skillset.paths import abbrev
from skillset.repo import clone_or_pull, get_repo_dir, parse_repo_spec

_MAX_RESOURCES = 200


def _split_repo_spec(query: list[str]) -> tuple[tuple[str, str] | None, list[str]]:
    """Split a leading `owner/repo` off a multi-term query, if there is one."""
    if len(query) < 2 or has_glob(query[0]) or "://" in query[0]:
        return None, query
    try:
        return parse_repo_spec(query[0]), query[1:]
    except ValueError:
        return None, query


def _ensure_repo(owner: str, repo: str) -> Path:
    """Directory of owner/repo, cloning it into the cache only if it isn't there yet.

    A repo cloned here is recorded as a trial repo (like `add --try`), so
    `skillset clean` removes it later. Repos that were already cached are
    left alone -- they may be ones the user wants to keep.
    """
    repo_dir = get_repo_dir(owner, repo)
    if not repo_dir.exists():
        try:
            repo_dir = clone_or_pull(owner, repo)
        except Exception as e:
            print(f"Could not fetch {owner}/{repo}: {e}", file=sys.stderr)
            sys.exit(1)
        record_install(f"{owner}/{repo}", scope="global", trial=True)
        print(
            f"Cloned {owner}/{repo} as a trial repo: 'skillset clean' removes it, "
            f"'skillset fetch {owner}/{repo}' keeps it.",
            file=sys.stderr,
        )
    return repo_dir.resolve() if is_link(repo_dir) else repo_dir


def _pick_skill(query: list[str]) -> tuple[str, Path, str]:
    """Return (source_key, skill_dir, name) for the single best match, or exit."""
    spec, query = _split_repo_spec(query)
    sources = [(f"{spec[0]}/{spec[1]}", _ensure_repo(*spec))] if spec else None
    matches = list(iter_matching_skills(query, sources))
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
    print("# Loaded on demand (not installed). Running `skillset get` means the user wants")
    print("# this skill applied: follow the instructions below as if it were an active skill.")
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
