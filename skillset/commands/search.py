"""Command handler for searching skills across cached and editable sources."""

from pathlib import Path

from skillset.discovery import find_skills, parse_skill_metadata
from skillset.linking import is_link
from skillset.paths import get_cache_dir, get_global_skillset_path, load_skillset


def _editable_sources() -> list[tuple[str, Path]]:
    """(toml_key, dir) for editable entries in the global skillset.yaml."""
    toml_path = get_global_skillset_path()
    if not toml_path.exists():
        return []
    config = load_skillset(toml_path)
    sources = []
    for key, value in (config.get("skills") or {}).items():
        if not isinstance(value, dict) or not value.get("editable"):
            continue
        source = value.get("source")
        if not source:
            continue
        source_dir = Path(source).expanduser().resolve()
        path_str = value.get("path")
        search_dir = source_dir / path_str if path_str else source_dir
        if search_dir.is_dir():
            sources.append((key, search_dir))
    return sources


def _cached_repos() -> list[tuple[str, Path]]:
    """(repo_key, dir) for every cached repo, resolving symlinks."""
    cache_dir = get_cache_dir()
    sources = []
    if not cache_dir.exists():
        return sources
    for owner_dir in sorted(cache_dir.iterdir()):
        if not owner_dir.is_dir() or owner_dir.name == "local":
            continue
        for repo_dir in sorted(owner_dir.iterdir()):
            if not repo_dir.is_dir():
                continue
            actual_dir = repo_dir.resolve() if is_link(repo_dir) else repo_dir
            sources.append((f"{owner_dir.name}/{repo_dir.name}", actual_dir))
    return sources


def _matches(terms: list[str], name: str, description: str) -> bool:
    haystack = f"{name} {description}".lower()
    return all(term in haystack for term in terms)


def cmd_search(query: list[str]) -> None:
    """Search skill names/descriptions across cached repos and editable sources."""
    terms = [q.lower() for q in query]
    seen: set[str] = set()
    results: dict[str, list[tuple[str, str]]] = {}

    for key, source_dir in _editable_sources() + _cached_repos():
        resolved = str(source_dir)
        if resolved in seen:
            continue
        seen.add(resolved)
        for skill_dir in find_skills(source_dir):
            name, description = parse_skill_metadata(skill_dir)
            if _matches(terms, name, description):
                results.setdefault(key, []).append((name, description))

    if not results:
        print("No matching skills found")
        return

    total = 0
    for key in sorted(results):
        print(f"{key}:")
        for name, description in sorted(results[key]):
            total += 1
            snippet = description[:100] + ("..." if len(description) > 100 else "")
            print(f"  {name} -- {snippet}" if snippet else f"  {name}")

    print(f"\n{total} skill(s) found. Install with: skillset add <repo> -s <skill>")
