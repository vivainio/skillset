"""UI helpers — prompts, local path handling, fzf integration."""

import subprocess
import sys
from pathlib import Path

from skillset.discovery import find_skills
from skillset.linking import (
    create_dir_link,
    get_copy_source,
    is_link,
    is_managed_copy,
    remove_link,
)
from skillset.paths import abbrev, get_cache_dir, get_global_skillset_path, load_skillset


def is_local_path(spec: str) -> bool:
    """Check if spec looks like a local path rather than owner/repo."""
    return spec.startswith(("/", ".", "~")) or Path(spec).expanduser().is_dir()


def register_local_lib(repo_dir: Path) -> None:
    """Register a local directory as a symlink under repos/local/ for tracking by update."""
    local_dir = get_cache_dir() / "local"
    local_dir.mkdir(parents=True, exist_ok=True)
    link_path = local_dir / repo_dir.name
    if is_link(link_path):
        remove_link(link_path)
    elif link_path.exists():
        return  # Don't overwrite non-link
    create_dir_link(link_path, repo_dir)


def find_skill(skill_name: str) -> list[tuple[Path, str, str | None, bool]]:
    """Search all sources for a skill by name.

    Searches editable sources in global skillset.yaml and cached repos.
    Returns list of (source_dir, toml_key, toml_source, is_editable) tuples.
    """
    matches: list[tuple[Path, str, str | None, bool]] = []
    seen_dirs: set[str] = set()

    _search_editable_sources(skill_name, matches, seen_dirs)
    _search_cached_repos(skill_name, matches, seen_dirs)

    return matches


def _search_editable_sources(skill_name, matches, seen_dirs):
    """Search editable entries in global skillset.yaml for a skill."""
    toml_path = get_global_skillset_path()
    if not toml_path.exists():
        return
    config = load_skillset(toml_path)
    for key, value in (config.get("skills") or {}).items():
        if not isinstance(value, dict) or not value.get("editable"):
            continue
        source = value.get("source")
        if not source:
            continue
        source_dir = Path(source).expanduser().resolve()
        path_str = value.get("path")
        search_dir = source_dir / path_str if path_str else source_dir
        if not search_dir.is_dir():
            continue
        if _has_skill(search_dir, skill_name):
            seen_dirs.add(str(search_dir))
            toml_source = str(search_dir).replace("\\", "/")
            matches.append((search_dir, key, toml_source, True))


def _search_cached_repos(skill_name, matches, seen_dirs):
    """Search cached repos for a skill."""
    cache_dir = get_cache_dir()
    if not cache_dir.exists():
        return
    for owner_dir in sorted(cache_dir.iterdir()):
        if not owner_dir.is_dir() or owner_dir.name == "local":
            continue
        for repo_dir in sorted(owner_dir.iterdir()):
            if not repo_dir.is_dir():
                continue
            actual_dir = repo_dir.resolve() if is_link(repo_dir) else repo_dir
            if str(actual_dir) in seen_dirs:
                continue
            if _has_skill(actual_dir, skill_name):
                toml_key = f"{owner_dir.name}/{repo_dir.name}"
                matches.append((actual_dir, toml_key, None, False))


def _has_skill(directory: Path, skill_name: str) -> bool:
    """Check if a directory contains a skill with the given name."""
    return any(s.name == skill_name for s in find_skills(directory))


def fzf_select(
    items: list[str], prompt: str = "Select> ", *, preserve_order: bool = False
) -> list[str]:
    """Run fzf for multi-select; returns selected items."""
    input_text = "\n".join(items)
    command = ["fzf", "--multi", "--prompt", prompt]
    if preserve_order:
        command.append("--no-sort")
    command.extend(["--header", "Tab to select, Enter to confirm"])
    result = subprocess.run(
        command,
        input=input_text,
        stdout=subprocess.PIPE,
        text=True,
    )
    if result.returncode not in (0, 1):
        print("fzf not found or failed", file=sys.stderr)
        sys.exit(1)
    return [line for line in result.stdout.splitlines() if line]


def fzf_select_installed_skills(skills: list[Path], prompt: str) -> list[str]:
    """Select installed skills, grouped and labelled by their source location."""
    groups: dict[str, list[str]] = {}
    for skill in skills:
        if is_managed_copy(skill):
            source = get_copy_source(skill) or "(copied)"
            location = abbrev(Path(source).expanduser().parent)
        else:
            location = abbrev(skill.resolve().parent)
        groups.setdefault(location, []).append(skill.name)
    items = [
        item
        for location in sorted(groups)
        for item in [f"# {location}", *(f"  {name}" for name in sorted(groups[location]))]
    ]
    selected = fzf_select(items, prompt=prompt, preserve_order=True)
    return [item.strip() for item in selected if not item.startswith("# ")]


def fzf_select_skills(skills: list[Path], repo_dir: Path, installed: set[str]) -> list[str]:
    """Interactive skill selection with group drill-down. Marks installed skills with *."""
    groups: dict[str, list[str]] = {}
    for skill in skills:
        group = skill.parent.name
        groups.setdefault(group, []).append(skill.name)

    def mark(name: str) -> str:
        return f"* {name}" if name in installed else f"  {name}"

    def unmark(item: str) -> str:
        return item.lstrip("* ").strip()

    def make_items(names: list[str]) -> list[str]:
        return [mark(n) for n in sorted(names)]

    if len(groups) <= 1:
        items = make_items(next(iter(groups.values()))) if groups else []
        selected = fzf_select(items, prompt="Skills> ")
        return [unmark(s) for s in selected]

    # Show default group flat, others as [group] entries
    default = "skills" if "skills" in groups else sorted(groups)[0]
    items = make_items(groups[default]) + sorted(f"[{g}]" for g in groups if g != default)
    selected = fzf_select(items, prompt="Skills> ")

    result = []
    for item in selected:
        if item.startswith("[") and item.endswith("]"):
            group_name = item[1:-1]
            sub = fzf_select(make_items(groups[group_name]), prompt=f"{group_name}> ")
            result.extend(unmark(s) for s in sub)
        else:
            result.append(unmark(item))
    return result


def prompt_skill_selection(
    available: list[Path],
) -> tuple[set[str] | None, list[str] | None, list[str] | None]:
    """Prompt user to add all or select individual skills.

    Returns (filter, enabled, disabled):
      - (None, ["*"], None): add all -- wildcard selection
      - (set, list, list): selective -- filter has names to install now,
        enabled/disabled are the explicit picks to persist in skillset.yaml
    """
    names = sorted(s.name for s in available)
    print(f"\n{len(names)} skill(s) found:")
    for name in names:
        print(f"  {name}")

    choice = input(f"\nAdd all {len(names)} skills? [Y/s(elect)] ").strip().lower()
    if choice in ("s", "select"):
        enabled: list[str] = []
        disabled: list[str] = []
        for name in names:
            answer = input(f"  Add {name}? [Y/n] ").strip().lower()
            if answer in ("n", "no"):
                disabled.append(name)
            else:
                enabled.append(name)
        return set(enabled), enabled, disabled
    # Default: add all -- wildcard
    return None, ["*"], None
