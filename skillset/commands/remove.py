"""Command handlers for removing skills."""

import fnmatch
import os
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
    abbrev,
    find_skillset_root,
    get_cache_dir,
    get_global_skills_dir,
    get_project_skills_dir,
)
from skillset.ui import fzf_select


def cmd_remove(*, name: str | None = None, g: bool = False, interactive: bool = False) -> None:
    """Remove a skill by name, or interactively select skills to remove."""
    skillset_root = None if g else find_skillset_root()
    if skillset_root:
        skills_dir = skillset_root / ".claude" / "skills"
    else:
        skills_dir = get_global_skills_dir()

    if interactive:
        installed = (
            sorted(p.name for p in skills_dir.iterdir() if is_managed(p))
            if skills_dir.exists()
            else []
        )
        if not installed:
            print(f"No managed skills in {abbrev(skills_dir)}")
            return
        scope = "project" if skillset_root else "global"
        selected = fzf_select(installed, prompt=f"Remove {scope} skills> ")
        for skill_name in selected:
            remove_managed(skills_dir / skill_name)
            print(f"Removed {skill_name} from {abbrev(skills_dir)}")
        return

    if not name:
        print("Provide a skill name or use -i for interactive selection")
        sys.exit(1)

    if has_glob(name):
        _remove_by_glob(skills_dir, name)
        return

    skill_path = skills_dir / name

    if not skill_path.exists():
        print(f"Skill '{name}' not found in {abbrev(skills_dir)}")
        sys.exit(1)

    if is_managed(skill_path):
        remove_managed(skill_path)
        print(f"Removed {name} from {abbrev(skills_dir)}")
    else:
        print(f"'{name}' is not managed by skillset - remove manually if intended")
        sys.exit(1)


def _remove_by_glob(skills_dir: Path, pattern: str) -> None:
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
    for name in matched:
        remove_managed(skills_dir / name)
        print(f"Removed {name} from {abbrev(skills_dir)}")


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
    cache_dir = get_cache_dir()
    repo_dir = cache_dir / repo_key.replace("/", os.sep)
    if not repo_dir.exists():
        return
    try:
        repo_dir.relative_to(cache_dir)
    except ValueError:
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
