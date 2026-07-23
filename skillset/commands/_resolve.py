"""Source resolution helpers for the add command."""

import sys
from pathlib import Path
from typing import NamedTuple

from skillset.linking import is_link
from skillset.paths import get_repo_roots
from skillset.repo import (
    clone_or_pull,
    clone_to_temp,
    get_repo_dir,
    parse_github_url,
    parse_repo_spec,
)
from skillset.ui import (
    find_skill,
    fzf_select,
    is_local_path,
)


class ResolvedSource(NamedTuple):
    """Source location and persistence metadata resolved for an add operation."""

    repo: str
    toml_key: str | None
    toml_source: str | None
    is_editable: bool
    repo_dir: Path
    temp_dir: Path | None
    source_label: str | None
    skills: list[str] | None
    subpath: str | None
    ref: str | None


def derive_toml_key_and_ref(repo: str, ref: str | None) -> tuple[str | None, str | None]:
    """Return (toml_key, effective_ref) for a repo string without cloning.

    For local paths and bare skill names there's no toml ref to compare against,
    so this returns (None, None).
    """
    if not repo or "://" in repo:
        if not repo:
            return None, None
        info = parse_github_url(repo)
        if not info:
            return None, None
        owner, repo_name, url_branch, _ = info
        return f"{owner}/{repo_name}", ref or url_branch
    if is_local_path(repo):
        return None, None
    if "/" in repo:
        try:
            owner, repo_name = parse_repo_spec(repo)
        except ValueError:
            return None, None
        return f"{owner}/{repo_name}", ref
    return None, None


def _resolve_source(
    repo: str | None,
    interactive: bool,
    skills: list[str] | None,
    subpath: str | None,
    no_cache: bool,
    ref: str | None = None,
) -> ResolvedSource | None:
    """Resolve the source repo/dir and metadata."""
    temp_dir = None
    source_label = None
    toml_key = None
    is_editable = False
    toml_source = None
    resolved_ref = ref

    if not repo:
        if not interactive:
            print("Provide a repo (e.g. skillset add owner/repo)")
            sys.exit(1)
        repo = _pick_repo_interactively()
        if not repo:
            return None

    if "://" in repo:
        repo_dir, toml_key, subpath, temp_dir, source_label, resolved_ref = _resolve_url(
            repo, subpath, no_cache, ref
        )
    elif is_local_path(repo):
        is_editable = True
        repo_dir, toml_key, toml_source = _resolve_local(repo)
        resolved_ref = None
    elif "/" in repo:
        repo_dir, toml_key, temp_dir, source_label = _resolve_spec(repo, no_cache, ref)
    else:
        is_editable, repo_dir, toml_key, toml_source, skills = _resolve_skill_name(repo, skills)
        resolved_ref = None

    return ResolvedSource(
        repo,
        toml_key,
        toml_source,
        is_editable,
        repo_dir,
        temp_dir,
        source_label,
        skills,
        subpath,
        resolved_ref,
    )


def _pick_repo_interactively() -> str | None:
    """Use fzf to pick a cached repo. Returns repo spec or None."""
    repos = set()
    for cache_dir in get_repo_roots():
        if not cache_dir.exists():
            continue
        for owner_dir in sorted(cache_dir.iterdir()):
            if owner_dir.is_dir():
                for repo_dir in sorted(owner_dir.iterdir()):
                    if repo_dir.is_dir():
                        repos.add(f"{owner_dir.name}/{repo_dir.name}")
    if not repos:
        print("No repos cached. Run 'skillset add owner/repo' first.")
        sys.exit(1)
    selected = fzf_select(sorted(repos), prompt="Repo> ")
    return selected[0] if selected else None


def _resolve_local(repo: str) -> tuple[Path, str, str]:
    """Resolve a local directory path. Returns (repo_dir, toml_key, toml_source)."""
    repo_dir = Path(repo).expanduser().resolve()
    if not repo_dir.is_dir():
        print(f"Directory not found: {repo_dir}")
        sys.exit(1)
    parent = repo_dir.parent.name
    toml_key = f"{parent}/{repo_dir.name}" if parent else repo_dir.name
    toml_source = str(repo_dir).replace("\\", "/")
    return repo_dir, toml_key, toml_source


def _resolve_skill_name(
    repo: str, skills: list[str] | None
) -> tuple[bool, Path, str | None, str | None, list[str]]:
    """Resolve a bare skill name by searching all sources.

    Returns (is_editable, repo_dir, toml_key, toml_source, skills).
    """
    matches = find_skill(repo)
    if not matches:
        print(f"Skill '{repo}' not found in any source")
        print("Add a source first: skillset add owner/repo or skillset add /path/to/skills")
        sys.exit(1)

    if len(matches) == 1:
        source_dir, toml_key, toml_source, is_editable = matches[0]
    else:
        print(f"\nSkill '{repo}' found in multiple sources:")
        for i, (_dir, _key, _source, _edit) in enumerate(matches, 1):
            label = _source or _key
            print(f"  {i}. {label}")
        choice = input(f"Choose source [1-{len(matches)}]: ").strip()
        try:
            idx = int(choice) - 1
            if not (0 <= idx < len(matches)):
                raise ValueError
        except ValueError:
            print("Invalid choice")
            sys.exit(1)
        source_dir, toml_key, toml_source, is_editable = matches[idx]

    if not skills:
        skills = [repo]
    return is_editable, source_dir, toml_key, toml_source, skills


def _resolve_url(
    repo: str,
    subpath: str | None,
    no_cache: bool,
    ref: str | None = None,
) -> tuple[Path, str, str | None, Path | None, str | None, str | None]:
    """Resolve a GitHub URL. Returns (repo_dir, toml_key, subpath, temp_dir, source_label, ref)."""
    github_info = parse_github_url(repo)
    if not github_info:
        print(f"Invalid GitHub URL: {repo}")
        sys.exit(1)
    owner, repo_name, url_branch, url_subpath = github_info
    toml_key = f"{owner}/{repo_name}"
    subpath = subpath or url_subpath
    ref = ref or url_branch
    temp_dir = None
    source_label = None
    if no_cache:
        repo_dir = clone_to_temp(owner, repo_name, ref)
        temp_dir = repo_dir.parent
        source_label = f"{owner}/{repo_name}"
    else:
        repo_dir = get_repo_dir(owner, repo_name)
        if is_link(repo_dir):
            repo_dir = repo_dir.resolve()
        else:
            repo_dir = clone_or_pull(owner, repo_name, ref)
    return repo_dir, toml_key, subpath, temp_dir, source_label, ref


def _resolve_spec(
    repo: str, no_cache: bool, ref: str | None = None
) -> tuple[Path, str, Path | None, str | None]:
    """Resolve an owner/repo spec. Returns (repo_dir, toml_key, temp_dir, source_label)."""
    try:
        owner, repo_name = parse_repo_spec(repo)
    except ValueError as e:
        print(str(e))
        sys.exit(1)
    toml_key = f"{owner}/{repo_name}"
    temp_dir = None
    source_label = None
    if no_cache:
        repo_dir = clone_to_temp(owner, repo_name, ref)
        temp_dir = repo_dir.parent
        source_label = f"{owner}/{repo_name}"
    else:
        repo_dir = get_repo_dir(owner, repo_name)
        if is_link(repo_dir):
            repo_dir = repo_dir.resolve()
        else:
            repo_dir = clone_or_pull(owner, repo_name, ref)
    return repo_dir, toml_key, temp_dir, source_label
