"""Command handlers for removing skills."""

import fnmatch
import shutil
import sys
from pathlib import Path

from skillset.linking import (
    get_copy_source,
    has_glob,
    is_link,
    is_managed,
    is_managed_copy,
    normalize_glob,
    remove_link,
    remove_managed,
)
from skillset.manifest import load_manifest, save_manifest
from skillset.paths import (
    SKILLSET_CONFIG_FILE,
    abbrev,
    find_skillset_root,
    get_global_commands_dir,
    get_global_skills_dir,
    get_global_skillset_path,
    get_project_skills_dir,
    get_repo_roots,
    load_skillset,
    remove_from_skillset,
    update_skillset_skills,
)
from skillset.repo import get_repo_dir
from skillset.ui import fzf_select_installed_skills


def cmd_remove(*, name: str | None = None, g: bool = False, interactive: bool = False) -> None:
    """Remove a skill by name, a repo (owner/repo) entirely, or interactively select skills."""
    if name and "/" in name:
        cmd_remove_repo(name, g=g)
        return

    skillset_root = None if g else find_skillset_root()
    if skillset_root:
        skills_dir = skillset_root / ".claude" / "skills"
    else:
        skills_dir = get_global_skills_dir()
    config_path = (
        skillset_root / SKILLSET_CONFIG_FILE if skillset_root else get_global_skillset_path()
    )

    if interactive:
        _remove_interactively(skills_dir, config_path, project=bool(skillset_root))
        return

    if not name:
        print("Provide a skill name or use -i for interactive selection")
        sys.exit(1)

    if has_glob(name):
        _remove_by_glob(skills_dir, name, config_path)
        return

    skill_path = skills_dir / name

    if not skill_path.exists():
        print(f"Skill '{name}' not found in {abbrev(skills_dir)}")
        sys.exit(1)

    if is_managed(skill_path):
        _persist_disabled(config_path, skills_dir, [name])
        remove_managed(skill_path)
        print(f"Removed {name} from {abbrev(skills_dir)}")
    else:
        print(f"'{name}' is not managed by skillset - remove manually if intended")
        sys.exit(1)


def _remove_interactively(skills_dir: Path, config_path: Path, *, project: bool) -> None:
    installed = (
        [p for p in skills_dir.iterdir() if p.is_dir() or p.is_symlink()]
        if skills_dir.exists()
        else []
    )
    if not installed:
        print(f"No skills in {abbrev(skills_dir)}")
        return
    scope = "project" if project else "global"
    selected = fzf_select_installed_skills(installed, prompt=f"Remove {scope} skills> ")
    _persist_disabled(config_path, skills_dir, selected)
    for skill_name in selected:
        skill_path = skills_dir / skill_name
        if is_managed(skill_path):
            remove_managed(skill_path)
        else:
            shutil.rmtree(skill_path)
        print(f"Removed {skill_name} from {abbrev(skills_dir)}")


def _remove_by_glob(skills_dir: Path, pattern: str, config_path: Path) -> None:
    """Remove skills matching a glob pattern."""
    if not skills_dir.exists():
        print(f"No skills in {abbrev(skills_dir)}")
        sys.exit(1)
    glob = normalize_glob(pattern)
    matched = sorted(
        p.name for p in skills_dir.iterdir() if fnmatch.fnmatch(p.name, glob) and is_managed(p)
    )
    if not matched:
        print(f"No managed skills matching '{pattern}' in {abbrev(skills_dir)}")
        sys.exit(1)
    _persist_disabled(config_path, skills_dir, matched)
    for name in matched:
        remove_managed(skills_dir / name)
        print(f"Removed {name} from {abbrev(skills_dir)}")


def _persist_disabled(config_path: Path, skills_dir: Path, names: list[str]) -> None:
    if not config_path.exists():
        return
    config = load_skillset(config_path)
    grouped: dict[str, list[str]] = {}
    for name in names:
        repo_key = _entry_for_source(config, config_path, skills_dir / name)
        if repo_key:
            grouped.setdefault(repo_key, []).append(name)
    for repo_key, disabled in grouped.items():
        if update_skillset_skills(config_path, repo_key, add_disabled=disabled):
            joined = ", ".join(disabled)
            print(f"Disabled {joined} in {abbrev(config_path)}")


def _entry_for_source(config, config_path: Path, skill_path: Path) -> str | None:
    source_text = _get_managed_source(skill_path)
    if not source_text:
        return None
    source = Path(source_text).expanduser()
    if source.is_absolute():
        source = source.resolve()
    for repo_key, entry in (config.get("skills") or {}).items():
        if not isinstance(entry, dict):
            continue
        if source_text == repo_key:
            return repo_key
        if entry.get("editable") and entry.get("source"):
            root = Path(entry["source"]).expanduser()
            if not root.is_absolute():
                root = config_path.parent / root
        else:
            root = get_repo_dir(*repo_key.split("/", 1))
        effective = root / entry["path"] if entry.get("path") else root
        try:
            source.relative_to(effective.resolve())
            return repo_key
        except ValueError:
            continue
    return None


def cmd_remove_repo(repo_key: str, *, g: bool = False) -> None:
    """Remove a repo entirely: its linked skills/commands, skillset.yaml entry, and cached clone."""
    skillset_root = None if g else find_skillset_root()
    is_local = skillset_root is not None
    skills_dir = (skillset_root / ".claude" / "skills") if is_local else get_global_skills_dir()
    commands_dir = (
        (skillset_root / ".claude" / "commands") if is_local else get_global_commands_dir()
    )
    toml_path = (skillset_root / SKILLSET_CONFIG_FILE) if is_local else get_global_skillset_path()

    removed = _remove_managed_from_source(skills_dir, repo_key, "skill")
    removed += _remove_managed_from_source(commands_dir, repo_key, "command")

    removed_from_toml = remove_from_skillset(toml_path, repo_key)
    if removed_from_toml:
        print(f"Removed {repo_key} from {abbrev(toml_path)}")

    repo_removed = _remove_cached_repo_dir(repo_key)

    manifest = load_manifest()
    if repo_key in manifest:
        del manifest[repo_key]
        save_manifest(manifest)

    if not removed and not removed_from_toml and not repo_removed:
        print(f"'{repo_key}' not found in {abbrev(toml_path)} or the cache")
        sys.exit(1)


def _remove_managed_from_source(target_dir: Path, repo_key: str, kind: str) -> int:
    """Remove managed items in target_dir sourced from repo_key. Returns count removed."""
    if not target_dir.exists():
        return 0
    removed = 0
    for item in sorted(target_dir.iterdir()):
        if not is_managed(item):
            continue
        source = _get_managed_source(item)
        if source is None:
            continue
        if repo_key in source or abbrev(repo_key) in abbrev(source):
            remove_managed(item)
            print(f"Removed {kind} {item.name}")
            removed += 1
    return removed


def _remove_cached_repo_dir(repo_key: str) -> bool:
    """Remove the cached clone for repo_key, if present. Returns True if removed."""
    repo_dir = get_repo_dir(*repo_key.split("/", 1))
    if not repo_dir.exists():
        return False
    if is_link(repo_dir):
        remove_link(repo_dir)
    else:
        shutil.rmtree(repo_dir)
    parent = repo_dir.parent
    if parent.exists() and parent not in get_repo_roots() and not any(parent.iterdir()):
        parent.rmdir()
    print(f"Removed cached repo {abbrev(repo_dir)}")
    return True


def cmd_clean(*, g: bool = False) -> None:
    """Remove all trial skills.

    Default: clean local trial skills if skillset.yaml found, otherwise global.
    With --global: clean global trial skills.
    """
    manifest = load_manifest()
    trial_repos = {k: v for k, v in manifest.items() if v.get("trial")}

    if not trial_repos:
        print("No trial skills to clean")
        return

    removed = 0
    for repo_key, opts in trial_repos.items():
        removed += _clean_trial_repo(repo_key, opts, manifest)

    save_manifest(manifest)
    print(f"Cleaned {removed} trial skill(s) from {len(trial_repos)} repo(s)")


def _resolve_clean_skills_dir(scope: str) -> Path | None:
    """Resolve skills directory for clean based on scope."""
    if scope == "local":
        clean_root = find_skillset_root()
        if clean_root:
            return clean_root / ".claude" / "skills"
        return get_project_skills_dir()
    return get_global_skills_dir()


def _get_managed_source(item: Path) -> str | None:
    """Get source path string for a managed skill item."""
    if is_managed_copy(item):
        return get_copy_source(item) or ""
    if is_link(item):
        return str(item.resolve())
    return None


def _clean_trial_repo(repo_key: str, opts: dict, manifest: dict) -> int:
    """Clean skills for a single trial repo. Returns count of removed skills."""
    skills_dir = _resolve_clean_skills_dir(opts.get("scope", "global"))
    if skills_dir is None:
        print(f"  Skipping {repo_key} (local scope, no skillset.yaml or git repo)")
        return 0

    removed = 0
    if skills_dir.exists():
        for item in sorted(skills_dir.iterdir()):
            if not is_managed(item):
                continue
            source = _get_managed_source(item)
            if source is None:
                continue
            if repo_key in source or abbrev(repo_key) in abbrev(source):
                remove_managed(item)
                print(f"  Removed {item.name}")
                removed += 1

    del manifest[repo_key]
    _remove_cached_repo(repo_key, manifest)
    return removed


def _remove_cached_repo(repo_key: str, manifest: dict) -> None:
    """Remove cached repo if no other manifest entries reference it."""
    remaining_keys = set(manifest.keys())
    repo_dir = get_repo_dir(*repo_key.split("/", 1))
    if not repo_dir.exists():
        return
    if not any(repo_dir.is_relative_to(root) for root in get_repo_roots()):
        return
    if any(k.startswith(repo_key) for k in remaining_keys):
        return
    if is_link(repo_dir):
        remove_link(repo_dir)
    else:
        shutil.rmtree(repo_dir)
    parent = repo_dir.parent
    if parent.exists() and not any(parent.iterdir()):
        parent.rmdir()
    print(f"  Removed cached repo {repo_key}")
