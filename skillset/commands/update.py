"""Command handler for update -- apply declared skills from skillset.yaml."""

import os
import subprocess
import sys
from fnmatch import fnmatchcase
from pathlib import Path

from skillset.discovery import find_skills
from skillset.linking import is_managed, link_commands, link_skills, remove_managed
from skillset.manifest import record_install
from skillset.paths import (
    SKILLSET_CONFIG_FILE,
    abbrev,
    find_skillset_root,
    get_global_commands_dir,
    get_global_skills_dir,
    get_global_skillset_path,
    load_skillset,
    update_skillset_skills,
)
from skillset.repo import clone_or_pull, parse_repo_spec


def _resolve_toml_path(file, g):
    """Resolve the skillset.yaml file path."""
    if file:
        return Path(file)
    if g:
        return get_global_skillset_path()
    skillset_root = find_skillset_root()
    if skillset_root:
        return skillset_root / SKILLSET_CONFIG_FILE
    return get_global_skillset_path()


def _is_glob(pattern: str) -> bool:
    """Check if a list entry is a glob pattern."""
    return any(c in pattern for c in "*?[")


def _expand_patterns(patterns: list[str], names: set[str]) -> set[str]:
    """Expand glob entries against available names. Literal entries pass through."""
    result: set[str] = set()
    for p in patterns:
        if _is_glob(p):
            result |= {n for n in names if fnmatchcase(n, p)}
        else:
            result.add(p)
    return result


def cmd_update(
    *,
    file: str | None = None,
    g: bool = False,
    new: str = "ask",
) -> None:
    """Update from skillset.yaml -- pull repos, link enabled, unlink disabled."""
    file_path = _resolve_toml_path(file, g)
    is_local = file_path != get_global_skillset_path()

    if not file_path.exists():
        print(f"No skillset.yaml at {abbrev(file_path)}")
        hint = "'skillset init'" if is_local else "'skillset init --global'"
        print(f"Run {hint} to create one.")
        sys.exit(1)

    config = load_skillset(file_path)
    _apply_links(config.get("links", {}))

    skills_config = config.get("skills") or {}
    if not skills_config:
        print("No skills entries in skillset.yaml")
        return

    skills_dir, commands_dir = _update_dirs(is_local, file_path)
    scope = "local" if is_local else "global"
    total_linked = 0
    new_skills_found: dict[str, list[str]] = {}
    new_skills_ctx: dict[str, tuple[Path, bool]] = {}

    for repo_key, value in skills_config.items():
        linked = _update_entry(
            repo_key,
            value,
            skills_dir,
            commands_dir,
            scope,
            new_skills_found,
            new_skills_ctx,
        )
        total_linked += linked

    total_linked += _prompt_for_new_skills(
        new_skills_found, new_skills_ctx, skills_dir, file_path, new
    )

    print(f"\nUpdate complete ({total_linked} skill(s) linked)")


def _apply_links(links_config):
    """Process the top-level `links:` section: arbitrary symlinks in the project."""
    for local_path, target in links_config.items():
        link = Path(local_path)
        if link.is_symlink():
            print(f"Link already exists: {local_path} -> {os.readlink(local_path)}")
        elif link.exists():
            print(f"Skipping {local_path}: exists and is not a symlink")
        else:
            link.parent.mkdir(parents=True, exist_ok=True)
            link.symlink_to(target)
            print(f"Linked {local_path} -> {target}")
        ignored = (
            subprocess.run(
                ["git", "check-ignore", "-q", local_path],
                capture_output=True,
            ).returncode
            == 0
        )
        if not ignored:
            print(f"  Warning: {local_path} is not in .gitignore")


def _update_dirs(is_local, file_path):
    """Return (skills_dir, commands_dir) for update."""
    if not is_local:
        return get_global_skills_dir(), get_global_commands_dir()
    root = file_path.parent
    return root / ".claude" / "skills", root / ".claude" / "commands"


def _update_entry(repo_key, value, skills_dir, commands_dir, scope, new_found, new_ctx):
    """Update a single entry. Returns count of linked skills."""
    if not isinstance(value, dict):
        print(f"\nSkipping {repo_key}: entry must be a sub-table")
        return 0
    return _update_dict_entry(
        repo_key,
        value,
        skills_dir,
        commands_dir,
        scope,
        new_found,
        new_ctx,
    )


def _update_dict_entry(
    repo_key,
    value,
    skills_dir,
    commands_dir,
    scope,
    new_found,
    new_ctx,
):
    """Update a sub-table entry with enabled/disabled lists."""
    if value.get("snapshot"):
        ref_str = value.get("ref")
        suffix = f" @ {ref_str[:7]}" if ref_str else ""
        print(f"\nSkipping {repo_key} (snapshot{suffix})")
        return 0

    editable = value.get("editable", False)
    path_str = value.get("path")
    source_str = value.get("source")
    ref_str = value.get("ref")
    use_copy = value.get("copy", False)
    enabled_raw = value.get("enabled")
    disabled_raw = value.get("disabled", [])

    if enabled_raw is not None and not isinstance(enabled_raw, list):
        print(f"\nSkipping {repo_key}: 'enabled' must be a list")
        return 0
    if not isinstance(disabled_raw, list):
        print(f"\nSkipping {repo_key}: 'disabled' must be a list")
        return 0

    source_dir, repo_dir, owner, repo_name = _resolve_update_source(
        repo_key,
        editable,
        source_str,
        path_str,
        ref_str,
    )
    if source_dir is None:
        return 0

    available = find_skills(source_dir)
    available_names = {s.name for s in available}
    disabled_set = _expand_patterns(disabled_raw, available_names)

    if enabled_raw is None:
        # No enabled key at all -- behave like ["*"] for ergonomics.
        enabled_declared = available_names - disabled_set
        tracked = available_names
    else:
        enabled_expanded = _expand_patterns(enabled_raw, available_names)
        enabled_declared = enabled_expanded - disabled_set
        # "new" = anything in available not yet matched by a pattern and not
        # listed literally. Patterns that hit a name suppress its prompt.
        literals = {p for p in (enabled_raw + disabled_raw) if not _is_glob(p)}
        tracked = enabled_expanded | disabled_set | literals

    total = _update_lists(
        enabled_declared,
        disabled_set,
        available_names,
        tracked,
        source_dir,
        skills_dir,
        commands_dir,
        use_copy,
        repo_key,
        new_found,
        new_ctx,
    )

    if not editable:
        record_install(
            f"{owner}/{repo_name}",
            subpath=path_str,
            copy=use_copy,
            scope=scope,
        )
    return total


def _last_commit_info(repo_dir: Path) -> str | None:
    """Return 'YYYY-MM-DD HH:MM (Nd ago) abc1234 subject' for HEAD, or None."""
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%cs %cr %h %s"],
            cwd=repo_dir,
            capture_output=True,
            text=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    return result.stdout.strip() or None


def _resolve_update_source(repo_key, editable, source_str, path_str, ref_str=None):
    """Resolve source directory for update."""
    owner = repo_name = None
    if editable:
        return _resolve_editable_source(repo_key, source_str, path_str, owner, repo_name)

    label = repo_key + (f"@{ref_str}" if ref_str else "")
    print(f"\nUpdating {label}...")
    try:
        owner, repo_name = parse_repo_spec(repo_key)
    except ValueError as e:
        print(f"  {e}")
        return None, None, None, None
    repo_dir = clone_or_pull(owner, repo_name, ref_str)
    last = _last_commit_info(repo_dir)
    if last:
        print(f"  latest commit: {last}")
    source_dir = repo_dir / path_str if path_str else repo_dir
    if path_str and not source_dir.is_dir():
        print(f"  Path not found in repo: {path_str}")
        return None, None, None, None
    return source_dir, repo_dir, owner, repo_name


def _resolve_editable_source(repo_key, source_str, path_str, owner, repo_name):
    """Resolve editable source directory for update."""
    if not source_str:
        print(f"\n{repo_key}: editable requires 'source' path")
        return None, None, None, None
    print(f"\nUpdating {repo_key} (editable)...")
    base_dir = Path(source_str).expanduser().resolve()
    source_dir = base_dir / path_str if path_str else base_dir
    if not source_dir.is_dir():
        if path_str:
            print(f"  Path not found: {path_str} in {source_str}")
        else:
            print(f"  Source not found: {source_str}")
        return None, None, None, None
    return source_dir, base_dir, owner, repo_name


def _update_lists(
    enabled_declared,
    disabled_set,
    available_names,
    tracked,
    source_dir,
    skills_dir,
    commands_dir,
    use_copy,
    repo_key,
    new_found,
    new_ctx,
):
    """Link enabled (minus missing), unlink disabled, report new untracked skills."""
    new = available_names - tracked
    if new:
        new_found[repo_key] = sorted(new)
        new_ctx[repo_key] = (source_dir, use_copy)

    to_link = enabled_declared & available_names
    total = 0
    if to_link:
        linked = link_skills(source_dir, skills_dir, only=to_link, copy=use_copy)
        total = len(linked)
        for name in sorted(linked):
            print(f"  + {name}")

    # Commands come along for the ride whenever we link anything from the source.
    link_commands(source_dir, commands_dir, copy=use_copy)

    for skill_name in sorted(disabled_set):
        skill_path = skills_dir / skill_name
        if skill_path.exists() and is_managed(skill_path):
            remove_managed(skill_path)
            print(f"  - {skill_name} (excluded)")

    # Clean up stale links for skills that were enabled but no longer exist in source.
    for skill_name in sorted(enabled_declared - available_names):
        skill_path = skills_dir / skill_name
        if is_managed(skill_path):
            remove_managed(skill_path)
            print(f"  - {skill_name} (removed from source)")

    return total


def _collect_new_skill_decisions(names, source_dir, skills_dir, use_copy, mode="ask"):
    """Collect user decisions for new skills. Returns (enabled, disabled, linked_count).

    mode: "ask" (prompt the user), "yes" (accept all), "no" (ignore all).
    """
    if mode == "yes":
        choice = "a"
    elif mode == "no":
        choice = "i"
    else:
        prompt = "\nAdd [a]ll / [i]gnore all / [s]elect individually? [a/i/s] "
        choice = input(prompt).strip().lower()

    if choice in ("a", "all"):
        linked = link_skills(source_dir, skills_dir, only=set(names), copy=use_copy)
        for name in names:
            print(f"  + {name}")
        return list(names), [], len(linked)
    if choice in ("i", "ignore"):
        for name in names:
            print(f"  - {name} (skipped)")
        return [], list(names), 0
    return _collect_individual_decisions(names, source_dir, skills_dir, use_copy)


def _collect_individual_decisions(names, source_dir, skills_dir, use_copy):
    """Collect individual yes/no decisions for each skill."""
    enabled: list[str] = []
    disabled: list[str] = []
    total = 0
    for name in names:
        accepted = input(f"  Add {name}? [y/N] ").strip().lower() in ("y", "yes")
        if accepted:
            enabled.append(name)
            total += len(link_skills(source_dir, skills_dir, only={name}, copy=use_copy))
            print(f"  + {name}")
        else:
            disabled.append(name)
            print(f"  - {name} (skipped)")
    return enabled, disabled, total


def _prompt_for_new_skills(new_skills_found, new_skills_ctx, skills_dir, file_path, mode="ask"):
    """Prompt user for new untracked skills. Returns count of linked skills."""
    if not new_skills_found:
        return 0

    total = 0
    print("\n--- New skills detected ---")
    for repo_key, names in new_skills_found.items():
        source_dir, use_copy = new_skills_ctx[repo_key]
        print(f"\n{repo_key}: {len(names)} new skill(s):")
        for name in names:
            print(f"  {name}")

        enabled, disabled, linked = _collect_new_skill_decisions(
            names, source_dir, skills_dir, use_copy, mode
        )
        total += linked

        if enabled or disabled:
            update_skillset_skills(
                file_path,
                repo_key,
                add_enabled=enabled,
                add_disabled=disabled,
            )
            print(f"  Updated {abbrev(file_path)}")

    return total
