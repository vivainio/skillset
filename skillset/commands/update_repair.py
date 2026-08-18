"""Detect and repair repositories configured both cached and editable."""

import re
import shutil
import subprocess
from pathlib import Path

from skillset.discovery import find_skills
from skillset.linking import has_glob
from skillset.paths import abbrev, get_repo_roots, resolve_editable_source, save_skillset
from skillset.repo import get_repo_dir


def _git_root_and_remote(source: Path) -> tuple[Path, str] | None:
    try:
        root = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=source,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        remote = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=root,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    repo_key = _repo_key_from_remote(remote)
    return (Path(root), repo_key) if repo_key else None


def _repo_key_from_remote(remote: str) -> str | None:
    match = re.search(r"(?:github\.com[:/])([^/]+/[^/]+?)(?:\.git)?$", remote)
    return match.group(1).removesuffix(".git") if match else None


def _duplicate_groups(config: dict, file_path: Path) -> dict[str, dict]:
    skills = config.get("skills") or {}
    groups: dict[str, dict] = {}
    for key, value in skills.items():
        if not isinstance(value, dict) or not value.get("editable"):
            continue
        source = value.get("source")
        if not source:
            continue
        source_path = resolve_editable_source(source, file_path)
        identity = _git_root_and_remote(source_path)
        if identity:
            root, repo_key = identity
            groups.setdefault(repo_key, {"root": root, "editable": []})["editable"].append(key)
    return {
        repo_key: group
        for repo_key, group in groups.items()
        if repo_key in skills and not skills[repo_key].get("editable")
    }


def report_or_repair_duplicate_sources(
    config: dict,
    file_path: Path,
    repair: bool = False,
    purge_candidates: list[tuple[str, Path]] | None = None,
) -> bool:
    """Report duplicate cached/editable repos; optionally consolidate safe groups."""
    groups = _duplicate_groups(config, file_path)
    missing = _missing_editable_entries(config, file_path) if repair else {}
    if not groups and not missing and not repair:
        return False
    if groups or missing:
        heading = "Configuration repair" if repair else "Duplicate repository sources"
        print(f"\n--- {heading} ---")
    changed = False
    for repo_key, group in groups.items():
        aliases = ", ".join(group["editable"])
        print(f"  {repo_key}: cached and editable via {aliases}")
        if repair:
            repaired = _repair_group(config, repo_key, group)
            changed |= repaired
    for key, source in missing.items():
        del config["skills"][key]
        print(f"  Removed {key}: source not found: {source}")
        changed = True
    if changed:
        save_skillset(file_path, config)
        print(f"  Repaired {abbrev(file_path)}")
    elif not repair:
        print("Run 'skillset update --repair' to consolidate safe duplicates.")
    if repair and purge_candidates is not None:
        purge_candidates.extend(_redundant_cache_candidates(config, file_path))
    return changed


def _redundant_cache_candidates(config: dict, file_path: Path) -> list[tuple[str, Path]]:
    candidates = {}
    for entry in (config.get("skills") or {}).values():
        if not isinstance(entry, dict) or not entry.get("editable") or entry.get("snapshot"):
            continue
        source = entry.get("source")
        if not source or entry.get("ref"):
            continue
        source_path = resolve_editable_source(source, file_path)
        identity = _git_root_and_remote(source_path)
        if not identity:
            continue
        root, repo_key = identity
        owner, repo = repo_key.split("/", 1)
        cache_dir = get_repo_dir(owner, repo)
        if cache_dir.exists() or cache_dir.is_symlink():
            candidates[repo_key] = root
    return list(candidates.items())


def remove_redundant_cached_repos(candidates: list[tuple[str, Path]], answer: str = "ask") -> None:
    """Offer to remove repaired cached clones after editable sources are linked."""
    for repo_key, editable_root in candidates:
        owner, repo = repo_key.split("/", 1)
        cache_dir = get_repo_dir(owner, repo)
        if not cache_dir.exists() and not cache_dir.is_symlink():
            continue
        if answer == "yes":
            remove = True
        elif answer == "ask":
            prompt = (
                f"Remove redundant cached clone for {repo_key}? "
                f"(editable at {abbrev(editable_root)}) [Y/n] "
            )
            remove = input(prompt).strip().lower() not in ("n", "no")
        else:
            print(f"Redundant cached clone remains at {abbrev(cache_dir)}")
            continue
        if remove:
            _remove_cache_dir(cache_dir)
            print(f"Removed cached clone {abbrev(cache_dir)}")
        else:
            print(f"Kept cached clone {abbrev(cache_dir)}")


def _remove_cache_dir(cache_dir: Path) -> None:
    if cache_dir.is_symlink():
        cache_dir.unlink()
    else:
        shutil.rmtree(cache_dir)
    parent = cache_dir.parent
    if parent not in get_repo_roots() and parent.exists() and not any(parent.iterdir()):
        parent.rmdir()


def _missing_editable_entries(config: dict, file_path: Path) -> dict[str, Path]:
    missing = {}
    for key, entry in (config.get("skills") or {}).items():
        if not isinstance(entry, dict) or not entry.get("editable") or not entry.get("source"):
            continue
        source = resolve_editable_source(entry["source"], file_path)
        effective = source / entry["path"] if entry.get("path") else source
        if not effective.is_dir():
            missing[key] = effective
    return missing


def _repair_group(config: dict, repo_key: str, group: dict) -> bool:
    skills = config["skills"]
    keys = [repo_key, *group["editable"]]
    entries = [skills[key] for key in keys]
    if any(entry.get("snapshot") or entry.get("ref") for entry in entries):
        print(f"  Skipping {repo_key}: snapshot/ref settings require manual repair")
        return False
    copy_modes = {bool(entry.get("copy")) for entry in entries}
    if len(copy_modes) > 1:
        print(f"  Skipping {repo_key}: conflicting copy settings require manual repair")
        return False

    enabled: set[str] = set()
    disabled: set[str] = set()
    for key, entry in zip(keys, entries, strict=True):
        source_dir = _entry_source_dir(key, entry, group["root"], repo_key)
        available = {skill.name for skill in find_skills(source_dir)}
        excluded = _expand(entry.get("disabled", []), available)
        declared = entry.get("enabled")
        selected = (
            available - excluded if declared is None else _expand(declared, available) - excluded
        )
        enabled |= selected
        disabled |= excluded

    replacement = {
        "editable": True,
        "source": str(group["root"]),
        "enabled": sorted(enabled),
    }
    remaining_disabled = sorted(disabled - enabled)
    if remaining_disabled:
        replacement["disabled"] = remaining_disabled
    if copy_modes == {True}:
        replacement["copy"] = True
    skills[repo_key] = replacement
    for key in group["editable"]:
        del skills[key]
    print(f"  Consolidated {repo_key} into editable source {group['root']}")
    return True


def _entry_source_dir(key: str, entry: dict, editable_root: Path, repo_key: str) -> Path:
    if key == repo_key:
        base = editable_root
    else:
        base = Path(entry["source"]).expanduser().resolve()
    path = entry.get("path")
    return base / path if path else base


def _expand(patterns: list[str], available: set[str]) -> set[str]:
    from fnmatch import fnmatchcase

    expanded = set()
    for pattern in patterns:
        if has_glob(pattern):
            glob = pattern.replace("%", "*")
            expanded |= {name for name in available if fnmatchcase(name, glob)}
        else:
            expanded.add(pattern)
    return expanded
