"""Command handler for installing skillset's own bundled skill."""

import importlib.resources
import sys
from pathlib import Path

from skillset.linking import copy_dir, is_managed, remove_managed
from skillset.paths import (
    abbrev,
    ensure_copilot_skills_symlink,
    find_skillset_root,
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


def cmd_install_skills(*, g: bool = False) -> None:
    """Install skillset's own usage-guide skill into Claude skills."""
    bundled = _bundled_skill_dir()
    if bundled is None:
        print("Bundled skill not found -- reinstall skillset to fix this")
        sys.exit(1)

    skillset_root = None if g else find_skillset_root()
    is_local = skillset_root is not None
    skills_dir = (skillset_root / ".claude" / "skills") if is_local else get_global_skills_dir()
    skills_dir.mkdir(parents=True, exist_ok=True)

    target = skills_dir / bundled.name
    if is_managed(target):
        remove_managed(target)
    elif target.exists():
        print(f"Skipping: {abbrev(target)} already exists (not managed by skillset)")
        return

    copy_dir(bundled, target, source_label="skillset (bundled)")
    print(f"Installed skillset skill to {abbrev(target)}")

    if not is_local and ensure_copilot_skills_symlink():
        print(f"Linked {abbrev(Path.home() / '.copilot' / 'skills')} -> {abbrev(skills_dir)}")
