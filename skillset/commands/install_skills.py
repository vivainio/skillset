"""Command handler for installing skillset's own bundled skill."""

import importlib.resources
import sys
from pathlib import Path

from skillset.linking import copy_dir
from skillset.paths import (
    abbrev,
    ensure_global_skills_symlinks,
    get_global_skills_dir,
)


def _bundled_skill_dir() -> Path | None:
    """Locate the skillset skill bundled inside the installed package."""
    try:
        root = importlib.resources.files("skillset") / "skill" / "skillset"
    except ModuleNotFoundError:
        return None
    path = Path(str(root))
    return path if path.is_dir() else None


def cmd_install_skills() -> None:
    """Install skillset's own usage-guide skill into global Claude skills."""
    bundled = _bundled_skill_dir()
    if bundled is None:
        print("Bundled skill not found -- reinstall skillset to fix this")
        sys.exit(1)

    skills_dir = get_global_skills_dir()
    skills_dir.mkdir(parents=True, exist_ok=True)

    target = skills_dir / bundled.name
    if target.is_symlink():
        target.unlink()
    copy_dir(bundled, target, source_label="skillset (bundled)")
    print(f"Installed skillset skill to {abbrev(target)}")

    ensure_global_skills_symlinks()
