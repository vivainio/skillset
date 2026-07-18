"""Saved snapshots of active global skills."""

from pathlib import Path

from skillset.linking import (
    copy_dir,
    create_dir_link,
    is_link,
    is_managed,
    is_managed_copy,
    remove_managed,
)
from skillset.paths import (
    get_global_skills_dir,
    get_profile_store_dir,
    get_profiles_path,
    load_skillset,
    save_skillset,
)


def load_profiles() -> dict:
    """Load profile data."""
    return load_skillset(get_profiles_path())


def profile_names() -> list[str]:
    """Return saved profile names."""
    return sorted((load_profiles().get("profiles") or {}).keys())


def active_profile() -> str | None:
    """Return the active profile name."""
    return load_profiles().get("active")


def _installed_skills() -> list[Path]:
    skills_dir = get_global_skills_dir()
    if not skills_dir.is_dir():
        return []
    return sorted(
        path
        for path in skills_dir.iterdir()
        if (path.is_dir() or path.is_symlink()) and (path / "SKILL.md").is_file()
    )


def _managed_entry(path: Path) -> dict | None:
    if is_link(path):
        return {"type": "link", "target": str(path.resolve())}
    return None


def _adopt(path: Path) -> dict:
    store = get_profile_store_dir()
    store.mkdir(parents=True, exist_ok=True)
    destination = store / path.name
    if destination.exists() or destination.is_symlink():
        raise ValueError(f"Cannot store {path.name}: {destination} already exists")
    path.rename(destination)
    try:
        create_dir_link(path, destination)
    except Exception:
        destination.rename(path)
        raise
    return {"type": "stored", "target": str(destination)}


def save_profile(name: str, include_unmanaged: bool = False) -> tuple[int, list[str]]:
    """Save the current global skills. Optionally adopt unmanaged directories."""
    entries = {}
    unmanaged = []
    installed = _installed_skills()
    to_store = [
        path
        for path in installed
        if is_managed_copy(path) or (include_unmanaged and not is_managed(path))
    ]
    collisions = [path.name for path in to_store if (get_profile_store_dir() / path.name).exists()]
    if collisions:
        names = ", ".join(collisions)
        raise ValueError(f"Cannot store skill(s); destination already exists: {names}")

    for path in installed:
        entry = _managed_entry(path)
        if entry:
            entries[path.name] = entry
        elif is_managed_copy(path) or include_unmanaged:
            entries[path.name] = _adopt(path)
        else:
            unmanaged.append(path.name)

    config_path = get_profiles_path()
    data = load_profiles()
    data.setdefault("profiles", {})[name] = {"skills": entries}
    data["active"] = name
    config_path.parent.mkdir(parents=True, exist_ok=True)
    save_skillset(config_path, data)
    return len(entries), unmanaged


def unmanaged_skill_names() -> list[str]:
    """Return installed skills not currently controlled by skillset."""
    return [path.name for path in _installed_skills() if not is_managed(path)]


def _known_skill_names(data: dict) -> set[str]:
    return {
        name
        for profile in (data.get("profiles") or {}).values()
        for name in (profile.get("skills") or {})
    }


def _activate_entry(name: str, entry: dict) -> bool:
    destination = get_global_skills_dir() / name
    target = Path(entry["target"]).expanduser()
    if not target.is_dir():
        print(f"  Missing {name}: source not found at {target}")
        return False
    if destination.exists() or destination.is_symlink():
        if not is_managed(destination):
            print(f"  Skipping {name}: an unmanaged skill uses that name")
            return False
        remove_managed(destination)
    if entry["type"] == "copy":
        copy_dir(target, destination, source_label=str(target))
    else:
        create_dir_link(destination, target)
    return True


def activate_profile(name: str) -> tuple[int, int]:
    """Reconcile known global skills to a saved profile."""
    data = load_profiles()
    profiles = data.get("profiles") or {}
    if name not in profiles:
        raise KeyError(name)
    skills_dir = get_global_skills_dir()
    skills_dir.mkdir(parents=True, exist_ok=True)
    selected = profiles[name].get("skills") or {}

    removed = 0
    for skill_name in _known_skill_names(data) - set(selected):
        path = skills_dir / skill_name
        if is_managed(path):
            remove_managed(path)
            removed += 1

    activated = sum(_activate_entry(skill_name, entry) for skill_name, entry in selected.items())
    data["active"] = name
    save_skillset(get_profiles_path(), data)
    return activated, removed


def delete_profile(name: str) -> None:
    """Delete a profile without deleting any stored skill contents."""
    path = get_profiles_path()
    data = load_profiles()
    profiles = data.get("profiles") or {}
    if name not in profiles:
        raise KeyError(name)
    del profiles[name]
    if data.get("active") == name:
        data["active"] = None
    save_skillset(path, data)
