"""Command handler for searching skills across cached and editable sources."""

import fnmatch
from collections.abc import Iterator
from pathlib import Path

from skillset.discovery import find_skills, parse_skill_metadata
from skillset.linking import has_glob, is_link, is_managed, normalize_glob
from skillset.paths import (
    get_global_skills_dir,
    get_global_skillset_path,
    get_profile_store_dir,
    get_repo_roots,
    load_skillset,
)


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
    """(repo_key, dir) for every stored repo, resolving symlinks."""
    sources = []
    seen = set()
    for root in get_repo_roots():
        if not root.exists():
            continue
        for owner_dir in sorted(root.iterdir()):
            if not owner_dir.is_dir() or owner_dir.name == "local":
                continue
            for repo_dir in sorted(owner_dir.iterdir()):
                key = f"{owner_dir.name}/{repo_dir.name}"
                if not repo_dir.is_dir() or key in seen:
                    continue
                seen.add(key)
                actual_dir = repo_dir.resolve() if is_link(repo_dir) else repo_dir
                sources.append((key, actual_dir))
    return sources


def _unmanaged_skills() -> list[tuple[str, Path]]:
    """Return installed and profile-stored unmanaged skills."""
    sources = []
    seen = set()
    skills_dir = get_global_skills_dir()
    if skills_dir.is_dir():
        for path in sorted(skills_dir.iterdir()):
            if is_managed(path) or not (path / "SKILL.md").is_file():
                continue
            seen.add(str(path.resolve()))
            sources.append(("Unmanaged", path))

    store = get_profile_store_dir()
    if store.is_dir():
        for path in sorted(store.iterdir()):
            if not (path / "SKILL.md").is_file() or str(path.resolve()) in seen:
                continue
            sources.append(("Saved unmanaged", path))
    return sources


def _term_matches(term: str, name: str, haystack: str) -> bool:
    """A single search term matches by substring, or by glob if it has wildcards.

    `*`/`?`/`[...]`/`%` (the shell-safe `*` alias) trigger fnmatch against the
    skill name and the full name+description haystack -- e.g. `jira-%` matches
    names starting with "jira-", `%config%` matches "config" anywhere.
    """
    if has_glob(term):
        pattern = normalize_glob(term)
        return fnmatch.fnmatch(name, pattern) or fnmatch.fnmatch(haystack, pattern)
    return term in haystack


def _matches(terms: list[str], name: str, description: str) -> bool:
    haystack = f"{name} {description}".lower()
    name = name.lower()
    return all(_term_matches(term, name, haystack) for term in terms)


def iter_matching_skills(
    query: list[str], sources: list[tuple[str, Path]] | None = None
) -> Iterator[tuple[str, Path, str, str]]:
    """Yield (source_key, skill_dir, name, description) for skills matching all terms.

    *sources* restricts the search to the given (key, dir) pairs; by default every
    known source is searched.
    """
    terms = [q.lower() for q in query]
    seen: set[str] = set()
    seen_skills: set[tuple[str, str]] = set()
    if sources is None:
        sources = _unmanaged_skills() + _editable_sources() + _cached_repos()
    for key, source_dir in sources:
        resolved = str(source_dir)
        if resolved in seen:
            continue
        seen.add(resolved)
        for skill_dir in find_skills(source_dir):
            name, description = parse_skill_metadata(skill_dir)
            # An editable checkout and the cached clone of the same repo share a
            # key; the earlier (editable) source wins so skills aren't listed twice.
            if (key, name) in seen_skills or not _matches(terms, name, description):
                continue
            seen_skills.add((key, name))
            yield key, skill_dir, name, description


def cmd_search(query: list[str]) -> None:
    """Search skill names/descriptions across cached repos and editable sources."""
    results: dict[str, list[tuple[str, str]]] = {}
    for key, _skill_dir, name, description in iter_matching_skills(query):
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

    print(
        f"\n{total} skill(s) found. Read one without installing: skillset get <skill>. "
        "Install with: skillset add <repo> -s <skill>"
    )
