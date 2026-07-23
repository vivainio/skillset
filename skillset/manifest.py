"""Install manifest — tracks per-repo install options."""

import json
from collections.abc import Mapping
from pathlib import Path
from typing import TypedDict

from skillset.paths import get_cache_dir, get_legacy_cache_dir


class InstallOptions(TypedDict):
    """Persisted installation settings for one repository."""

    subpath: str | None
    copy: bool
    scope: str
    trial: bool


Manifest = dict[str, InstallOptions]


def get_manifest_path() -> Path:
    """Get the path to the install manifest."""
    return get_cache_dir() / "manifest.json"


def load_manifest() -> Manifest:
    """Load the install manifest (tracks per-repo install options)."""
    path = get_manifest_path()
    if path.exists():
        return json.loads(path.read_text())
    legacy = get_legacy_cache_dir() / "manifest.json"
    if legacy.exists():
        return json.loads(legacy.read_text())
    return {}


def save_manifest(manifest: Mapping[str, object]) -> None:
    """Save the install manifest."""
    path = get_manifest_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2) + "\n")


def record_install(
    repo_key: str,
    *,
    subpath: str | None = None,
    copy: bool = False,
    scope: str = "global",
    trial: bool | None = None,
) -> None:
    """Record install options for a repo in the manifest.

    trial=True/False explicitly sets the flag; trial=None preserves the existing value.
    """
    manifest = load_manifest()
    existing = manifest.get(repo_key, {})
    entry: InstallOptions = {
        "subpath": subpath,
        "copy": copy,
        "scope": scope,
        "trial": existing.get("trial", False) if trial is None else trial,
    }
    manifest[repo_key] = entry
    save_manifest(manifest)


def get_install_options(repo_key: str) -> InstallOptions | None:
    """Get saved install options for a repo."""
    return load_manifest().get(repo_key)
