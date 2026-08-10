"""Command handler for listing installed skills."""

import os
from collections.abc import Callable
from pathlib import Path

from skillset.commands.search import _cached_repos, _editable_sources
from skillset.discovery import find_skills, parse_skill_metadata
from skillset.linking import (
    get_copy_source,
    is_link,
    is_managed,
    is_managed_copy,
    remove_link,
)
from skillset.manifest import load_manifest
from skillset.paths import (
    abbrev,
    find_skillset_root,
    get_global_agents_dir,
    get_global_commands_dir,
    get_global_skills_dir,
    get_profile_store_dir,
    get_project_agents_dir,
    get_project_commands_dir,
    get_project_skills_dir,
    get_repo_roots,
)


def _is_trial_skill(item: Path, trial_repos: set[str]) -> bool:
    """Check if a skill belongs to a trial repo."""
    if is_managed_copy(item):
        source = get_copy_source(item) or ""
    elif is_link(item):
        source = str(item.resolve().parent)
    else:
        return False
    return any(key in source or abbrev(key) in abbrev(source) for key in trial_repos)


def _print_grouped(
    items: list[Path],
    is_link_fn: Callable[[Path], bool],
    label: str,
    install_dir: Path,
    trial_repos: set[str],
    prune: bool,
    show_description_size: bool = False,
) -> None:
    """Print items grouped by source directory."""
    if not items:
        return
    print(f"{label} ({abbrev(install_dir)}):")
    groups: dict[str, list[tuple[str, str]]] = {}
    broken: list[Path] = []
    for item in items:
        target_dir = _resolve_target_dir(item, is_link_fn, broken)
        if target_dir is None:
            continue
        trial_tag = " (trial)" if _is_trial_skill(item, trial_repos) else ""
        if show_description_size:
            _, description = parse_skill_metadata(item)
            suffix = f"({len(description)} chars){trial_tag}"
        else:
            suffix = trial_tag
        display_name = item.relative_to(install_dir).as_posix()
        groups.setdefault(target_dir, []).append((display_name, suffix))
    for target_dir, entries in sorted(groups.items()):
        print(f"  {target_dir}:")
        name_width = max(len(name) for name, _ in entries)
        for name, suffix in sorted(entries):
            spacing = "  " if suffix else ""
            print(f"    {name:<{name_width}}{spacing}{suffix}")
    for item in broken:
        if prune:
            remove_link(item)
            print(f"  [pruned broken link: {item.name}]")
        else:
            print(f"  [broken link: {item.name}]")


def _resolve_target_dir(
    item: Path, is_link_fn: Callable[[Path], bool], broken: list[Path]
) -> str | None:
    """Resolve display target directory for a skill/command item."""
    if not is_link_fn(item):
        return "Unmanaged"
    if is_managed_copy(item):
        source = get_copy_source(item)
        return abbrev(source) if source else "(copied)"
    resolved = item.resolve()
    if not resolved.exists():
        broken.append(item)
        return None
    if resolved.parent == get_profile_store_dir().resolve():
        return "Unmanaged"
    return abbrev(resolved.parent)


def _list_repos(cache_dir: Path) -> list[str]:
    """Collect cached repo names."""
    repos = []
    if cache_dir.exists():
        for owner_dir in sorted(cache_dir.iterdir()):
            if owner_dir.is_dir():
                for repo_dir in sorted(owner_dir.iterdir()):
                    if repo_dir.is_dir():
                        repos.append(f"{owner_dir.name}/{repo_dir.name}")
    return repos


def _resolve_project_dirs() -> tuple[Path | None, Path | None, Path | None]:
    """Resolve project artifact dirs with skillset.yaml fallback."""
    skills_dir = get_project_skills_dir()
    commands_dir = get_project_commands_dir()
    agents_dir = get_project_agents_dir()
    if skills_dir is None or commands_dir is None or agents_dir is None:
        skillset_root = find_skillset_root()
        if skillset_root:
            if skills_dir is None:
                skills_dir = skillset_root / ".claude" / "skills"
            if commands_dir is None:
                commands_dir = skillset_root / ".claude" / "commands"
            if agents_dir is None:
                agents_dir = skillset_root / ".claude" / "agents"
    return skills_dir, commands_dir, agents_dir


def _dir_contents(d: Path | None) -> list[Path]:
    """Return sorted contents of a directory, or empty list."""
    if d and d.exists():
        return sorted(d.iterdir())
    return []


def _print_repos(cache_dir: Path, repos: list[str]) -> None:
    """Print cached repos."""
    print(f"Repos ({abbrev(cache_dir)}):")
    for repo in repos:
        repo_path = cache_dir / repo.replace("/", os.sep)
        if is_link(repo_path):
            print(f"  {repo} -> {abbrev(repo_path.resolve())}")
        else:
            print(f"  {repo}")


def _print_available(installed: set[str]) -> None:
    """Print skills from cached repos / editable sources that aren't installed."""
    results: dict[str, list[tuple[str, str]]] = {}
    seen: set[str] = set()
    for key, source_dir in _editable_sources() + _cached_repos():
        resolved = str(source_dir)
        if resolved in seen:
            continue
        seen.add(resolved)
        for skill_dir in find_skills(source_dir):
            if skill_dir.name in installed:
                continue
            _, description = parse_skill_metadata(skill_dir)
            results.setdefault(key, []).append((skill_dir.name, description))

    if not results:
        print("No available skills found -- everything cached is already installed")
        return

    total = 0
    for key in sorted(results):
        print(f"{key}:")
        for name, description in sorted(results[key]):
            total += 1
            snippet = description[:100] + ("..." if len(description) > 100 else "")
            print(f"  {name} -- {snippet}" if snippet else f"  {name}")

    print(f"\n{total} skill(s) available. Install with: skillset add <repo> -s <skill>")


def cmd_list(*, prune: bool = False, available: bool = False) -> None:
    """List installed skills and commands."""
    global_skills_dir = get_global_skills_dir()
    project_skills_dir, project_commands_dir, project_agents_dir = _resolve_project_dirs()

    global_skills = _dir_contents(global_skills_dir)
    project_skills = _dir_contents(project_skills_dir)

    if available:
        installed = {p.name for p in global_skills} | {p.name for p in project_skills}
        _print_available(installed)
        return

    global_commands_dir = get_global_commands_dir()
    global_commands = _dir_contents(global_commands_dir)
    project_commands = _dir_contents(project_commands_dir)
    global_agents_dir = get_global_agents_dir()
    global_agents = sorted(global_agents_dir.rglob("*.md")) if global_agents_dir.exists() else []
    project_agents = (
        sorted(project_agents_dir.rglob("*.md"))
        if project_agents_dir and project_agents_dir.exists()
        else []
    )

    manifest = load_manifest()
    trial_repos = {k for k, v in manifest.items() if v.get("trial")}

    def pg(
        items: list[Path],
        fn: Callable[[Path], bool],
        label: str,
        d: Path,
        show_description_size: bool = False,
    ) -> None:
        _print_grouped(
            items,
            fn,
            label,
            d,
            trial_repos,
            prune,
            show_description_size=show_description_size,
        )

    pg(global_skills, is_managed, "Global skills", global_skills_dir, True)
    if project_skills_dir:
        pg(project_skills, is_managed, "Project skills", project_skills_dir, True)
    pg(global_commands, lambda p: p.is_symlink(), "Global commands", global_commands_dir)
    if project_commands_dir:
        pg(project_commands, lambda p: p.is_symlink(), "Project commands", project_commands_dir)
    pg(global_agents, lambda p: p.is_symlink(), "Global agents", global_agents_dir)
    if project_agents_dir:
        pg(project_agents, lambda p: p.is_symlink(), "Project agents", project_agents_dir)

    repo_groups = [(root, _list_repos(root)) for root in get_repo_roots()]
    for root, repos in repo_groups:
        if repos:
            _print_repos(root, repos)

    has_repos = any(repos for _, repos in repo_groups)
    has_anything = (
        global_skills
        or project_skills
        or global_commands
        or project_commands
        or global_agents
        or project_agents
        or has_repos
    )
    if not has_anything:
        print("No skills, commands, or repos found (including no agents)")
