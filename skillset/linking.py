"""Linking and copying — symlinks, junctions, managed copies."""

import difflib
import fnmatch
import os
import shutil
import subprocess
from pathlib import Path

from skillset.discovery import find_agents, find_commands, find_skills
from skillset.paths import IS_WINDOWS

SKILLSET_SOURCE_MARKER = ".skillset-source"

# `%` is accepted as a shell-safe alias for the `*` wildcard: bash/zsh/fish/nu
# all leave `%` untouched, so `bf-%` survives without quoting where `bf-*` would
# be glob-expanded (or rejected) by the shell before skillset ever sees it.
GLOB_CHARS = "*?[%"


def has_glob(name: str) -> bool:
    """True if name is a wildcard pattern (including the `%` alias)."""
    return any(c in name for c in GLOB_CHARS)


def normalize_glob(pattern: str) -> str:
    """Translate the shell-safe `%` wildcard alias to fnmatch's `*`."""
    return pattern.replace("%", "*")


def create_dir_link(link_path: Path, target_path: Path) -> None:
    """Create a directory link (junction on Windows, symlink on Unix)."""
    if IS_WINDOWS:
        # Use junction on Windows (no admin required)
        subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(link_path), str(target_path)],
            check=True,
            capture_output=True,
        )
    else:
        link_path.symlink_to(target_path)


def is_link(path: Path) -> bool:
    """Check if path is a symlink or junction."""
    if path.is_symlink():
        return True
    if IS_WINDOWS:
        # Path.is_junction() added in Python 3.12
        if hasattr(path, "is_junction"):
            return path.is_junction()
        # Python 3.11 fallback: check reparse point file attribute
        try:
            import stat as stat_mod

            return bool(os.lstat(path).st_file_attributes & stat_mod.FILE_ATTRIBUTE_REPARSE_POINT)
        except (OSError, AttributeError):
            return False
    return False


def remove_link(path: Path) -> None:
    """Remove a symlink or junction."""
    if IS_WINDOWS and path.is_dir():
        # Junctions need rmdir, not unlink
        os.rmdir(path)
    else:
        path.unlink()


def fuzzy_match(name: str, candidates: list[str], cutoff: float = 0.6) -> str | None:
    """Find the best fuzzy match for name among candidates."""
    matches = difflib.get_close_matches(name, candidates, n=1, cutoff=cutoff)
    return matches[0] if matches else None


def is_managed_copy(path: Path) -> bool:
    """Check if path is a skillset-managed copy (has marker file)."""
    return path.is_dir() and (path / SKILLSET_SOURCE_MARKER).is_file()


def get_copy_source(path: Path) -> str | None:
    """Get the source path from a managed copy's marker file."""
    marker = path / SKILLSET_SOURCE_MARKER
    if marker.is_file():
        return marker.read_text().strip()
    return None


def is_managed(path: Path) -> bool:
    """Check if path is managed by skillset (link or copy)."""
    return is_link(path) or is_managed_copy(path)


def remove_managed(path: Path) -> None:
    """Remove a managed skill (link or copy)."""
    if is_link(path):
        remove_link(path)
    elif is_managed_copy(path):
        shutil.rmtree(path)
    else:
        raise ValueError(f"Not a managed path: {path}")


def copy_dir(src: Path, dst: Path, source_label: str | None = None) -> None:
    """Copy a directory and write a marker file recording the source."""
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    (dst / SKILLSET_SOURCE_MARKER).write_text((source_label or str(src)) + "\n")


def _resolve_skill_filter(
    only: set[str] | None, available_names: list[str], target_dir: Path, existing_only: bool
) -> set[str] | None:
    """Resolve the skill name filter: apply existing_only, expand globs, fuzzy-match."""
    quiet_missing = existing_only and only is None
    if existing_only:
        existing = {p.name for p in target_dir.iterdir() if p.is_dir() or p.is_symlink()}
        only = (only & existing) if only is not None else existing

    if only is None:
        return None

    verified = set()
    for name in only:
        if has_glob(name):
            matched = fnmatch.filter(available_names, normalize_glob(name))
            if matched:
                verified.update(matched)
            elif not quiet_missing:
                print(f"  Pattern '{name}' matched no skills")
        elif name in available_names:
            verified.add(name)
        elif not quiet_missing:
            suggestion = fuzzy_match(name, available_names)
            if suggestion:
                print(f"  Skill '{name}' not found. Did you mean '{suggestion}'?")
            else:
                print(f"  Skill '{name}' not found (no close match)")
    return verified


def link_skills(
    repo_dir: Path,
    target_dir: Path,
    only: set[str] | None = None,
    copy: bool = False,
    source_label: str | None = None,
    existing_only: bool = False,
) -> list[str]:
    """Link (or copy) skill directories from repo to target skills dir."""
    target_dir.mkdir(parents=True, exist_ok=True)
    available = find_skills(repo_dir)
    available_names = [s.name for s in available]

    only = _resolve_skill_filter(only, available_names, target_dir, existing_only)

    linked = []
    for skill_dir in available:
        skill_name = skill_dir.name
        if only is not None and skill_name not in only:
            continue
        link_path = target_dir / skill_name
        if is_managed(link_path):
            remove_managed(link_path)
        elif link_path.exists():
            print(f"  Skipping {skill_name}: already exists (not managed by skillset)")
            continue
        if copy:
            copy_dir(skill_dir, link_path, source_label=source_label)
        else:
            create_dir_link(link_path, skill_dir)
        linked.append(skill_name)
    return linked


def link_commands(
    repo_dir: Path,
    target_dir: Path,
    only: set[str] | None = None,
    copy: bool = False,
    existing_only: bool = False,
) -> list[str]:
    """Link (or copy) command files from repo to target commands dir."""
    target_dir.mkdir(parents=True, exist_ok=True)
    if existing_only:
        existing = {p.name for p in target_dir.iterdir() if p.is_file() or p.is_symlink()}
        if only is not None:
            only = only & existing
        else:
            only = existing
    linked = []
    for cmd_file in find_commands(repo_dir):
        cmd_name = cmd_file.name
        if only is not None and cmd_name not in only:
            continue
        link_path = target_dir / cmd_name
        if link_path.is_symlink():
            link_path.unlink()
        elif link_path.exists():
            if copy:
                link_path.unlink()
            else:
                print(f"  Skipping {cmd_name}: already exists (not a link)")
                continue
        if copy:
            shutil.copy2(cmd_file, link_path)
        else:
            link_path.symlink_to(cmd_file)
        linked.append(cmd_name)
    return linked


def remove_unselected_commands(repo_dir: Path, target_dir: Path, keep: set[str]) -> None:
    """Remove linked commands sourced from repo_dir unless their filenames are kept.

    `keep` entries are filenames (with `.md`), matching `link_commands`'s return format.
    """
    if not target_dir.exists():
        return
    source = repo_dir.resolve()
    for item in sorted(target_dir.glob("*.md")):
        if item.name in keep or not item.is_symlink():
            continue
        try:
            item.resolve().relative_to(source)
        except ValueError:
            continue
        item.unlink()


def link_agents(
    repo_dir: Path,
    target_dir: Path,
    only: set[str] | None = None,
    copy: bool = False,
) -> list[str]:
    """Link or copy Claude agents, preserving paths below each agents root."""
    discovered = find_agents(repo_dir)
    relative_paths = [relative for _, relative in discovered]
    duplicates = {path for path in relative_paths if relative_paths.count(path) > 1}
    if duplicates:
        names = ", ".join(sorted(path.as_posix() for path in duplicates))
        print(f"  Skipping conflicting agent path(s): {names}")

    linked = []
    for agent_file, relative in discovered:
        if relative in duplicates:
            continue
        agent_name = relative.with_suffix("").as_posix()
        if only is not None and agent_name not in only:
            continue
        link_path = target_dir / relative
        link_path.parent.mkdir(parents=True, exist_ok=True)
        if link_path.is_symlink():
            link_path.unlink()
        elif link_path.exists():
            if copy:
                link_path.unlink()
            else:
                print(f"  Skipping {relative.as_posix()}: already exists (not a link)")
                continue
        if copy:
            shutil.copy2(agent_file, link_path)
        else:
            link_path.symlink_to(agent_file)
        linked.append(agent_name)
    return linked


def remove_unselected_agents(repo_dir: Path, target_dir: Path, keep: set[str]) -> None:
    """Remove linked agents sourced from repo_dir unless their names are kept."""
    if not target_dir.exists():
        return
    source = repo_dir.resolve()
    for item in sorted(target_dir.rglob("*.md")):
        name = item.relative_to(target_dir).with_suffix("").as_posix()
        if name in keep or not item.is_symlink():
            continue
        try:
            item.resolve().relative_to(source)
        except ValueError:
            continue
        item.unlink()
    for directory in sorted(
        (path for path in target_dir.rglob("*") if path.is_dir()), reverse=True
    ):
        if not any(directory.iterdir()):
            directory.rmdir()
