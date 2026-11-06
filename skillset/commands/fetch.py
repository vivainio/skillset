"""Command handler for fetching a repo into the cache without linking anything."""

import shutil
import sys

from skillset.commands._resolve import _resolve_source
from skillset.commands.add import (
    _check_ref_conflict,
    _ensure_toml_exists,
    _register_in_toml,
    _reuse_registered_editable,
)
from skillset.discovery import find_skills
from skillset.paths import abbrev, find_skillset_root


def cmd_fetch(
    *,
    repo: str | None = None,
    g: bool = False,
    subpath: str | None = None,
    ref: str | None = None,
) -> None:
    """Clone/cache a repo and register it with no skills enabled -- link nothing.

    The repo's skills become findable with `search` and readable with `get`.
    """
    skillset_root = None if g else find_skillset_root()
    is_local = skillset_root is not None

    if not _check_ref_conflict(repo, ref, is_local, skillset_root, False):
        return

    resolved = _resolve_source(repo, False, None, subpath, False, ref)
    if resolved is None:
        return
    _repo, toml_key, toml_source, is_editable, repo_dir, temp_dir, _label, _skills, subpath, ref = (
        resolved
    )

    toml_key, toml_source = _reuse_registered_editable(
        repo_dir, toml_key, toml_source, is_editable, is_local, skillset_root
    )

    source_dir = repo_dir / subpath if subpath else repo_dir
    if subpath and not source_dir.is_dir():
        print(f"Path not found in repo: {subpath}")
        sys.exit(1)

    print(f"Fetched {abbrev(repo_dir)}")
    if toml_key:
        disabled = sorted(s.name for s in find_skills(source_dir))
        _ensure_toml_exists(is_editable, is_local, skillset_root)
        _register_in_toml(
            toml_key,
            subpath,
            [],
            disabled,
            [],
            [],
            is_editable,
            toml_source,
            is_local,
            skillset_root,
            ref,
            False,
            False,
        )
    if temp_dir:
        shutil.rmtree(temp_dir, ignore_errors=True)
