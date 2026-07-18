"""Detect and repair repositories configured both cached and editable."""

import re
import subprocess
from pathlib import Path

from skillset.discovery import find_skills
from skillset.linking import has_glob
from skillset.paths import abbrev, save_skillset


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


def _duplicate_groups(config, file_path):
    skills = config.get("skills") or {}
    groups: dict[str, dict] = {}
    for key, value in skills.items():
        if not isinstance(value, dict) or not value.get("editable"):
            continue
        source = value.get("source")
        if not source:
            continue
        source_path = Path(source).expanduser()
        if not source_path.is_absolute():
            source_path = file_path.parent / source_path
        identity = _git_root_and_remote(source_path.resolve())
        if identity:
            root, repo_key = identity
            groups.setdefault(repo_key, {"root": root, "editable": []})["editable"].append(key)
    return {
        repo_key: group
        for repo_key, group in groups.items()
        if repo_key in skills and not skills[repo_key].get("editable")
    }


def report_or_repair_duplicate_sources(config, file_path, repair=False):
    """Report duplicate cached/editable repos; optionally consolidate safe groups."""
    groups = _duplicate_groups(config, file_path)
    missing = _missing_editable_entries(config, file_path) if repair else {}
    if not groups and not missing:
        return False
    heading = "Configuration repair" if repair else "Duplicate repository sources"
    print(f"\n--- {heading} ---")
    changed = False
    for repo_key, group in groups.items():
        aliases = ", ".join(group["editable"])
        print(f"  {repo_key}: cached and editable via {aliases}")
        if repair:
            changed |= _repair_group(config, repo_key, group)
    for key, source in missing.items():
        del config["skills"][key]
        print(f"  Removed {key}: source not found: {source}")
        changed = True
    if changed:
        save_skillset(file_path, config)
        print(f"  Repaired {abbrev(file_path)}")
    elif not repair:
        print("Run 'skillset update --repair' to consolidate safe duplicates.")
    return changed


def _missing_editable_entries(config, file_path):
    missing = {}
    for key, entry in (config.get("skills") or {}).items():
        if not isinstance(entry, dict) or not entry.get("editable") or not entry.get("source"):
            continue
        source = Path(entry["source"]).expanduser()
        if not source.is_absolute():
            source = file_path.parent / source
        effective = source / entry["path"] if entry.get("path") else source
        if not effective.is_dir():
            missing[key] = effective
    return missing


def _repair_group(config, repo_key, group):
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


def _entry_source_dir(key, entry, editable_root, repo_key):
    if key == repo_key:
        base = editable_root
    else:
        base = Path(entry["source"]).expanduser().resolve()
    path = entry.get("path")
    return base / path if path else base


def _expand(patterns, available):
    from fnmatch import fnmatchcase

    expanded = set()
    for pattern in patterns:
        if has_glob(pattern):
            glob = pattern.replace("%", "*")
            expanded |= {name for name in available if fnmatchcase(name, glob)}
        else:
            expanded.add(pattern)
    return expanded
