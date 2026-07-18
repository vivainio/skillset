"""Interactive global skill profiles."""

from skillset.profiles import (
    activate_profile,
    active_profile,
    delete_profile,
    profile_names,
    save_profile,
    unmanaged_skill_names,
)
from skillset.ui import select_one


def _switch(name: str) -> None:
    try:
        activated, removed = activate_profile(name)
    except KeyError:
        print(f"Profile '{name}' not found")
        return
    print(f"Activated profile '{name}' ({activated} active, {removed} removed)")


def _save() -> None:
    name = input("Profile name: ").strip()
    if not name:
        print("Profile not saved")
        return
    if name in profile_names():
        answer = input(f"Replace existing profile '{name}'? [y/N] ").strip().lower()
        if answer not in ("y", "yes"):
            print("Profile not saved")
            return
    unmanaged = unmanaged_skill_names()
    include = False
    if unmanaged:
        print(f"\nFound {len(unmanaged)} unmanaged skill(s): {', '.join(unmanaged)}")
        answer = input("Include and store them in this profile? [y/N] ").strip().lower()
        include = answer in ("y", "yes")
    try:
        count, skipped = save_profile(name, include_unmanaged=include)
    except (OSError, ValueError) as error:
        print(f"Could not save profile: {error}")
        return
    print(f"Saved profile '{name}' with {count} skill(s)")
    if skipped:
        print(f"Left unmanaged: {', '.join(skipped)}")


def _delete() -> None:
    names = profile_names()
    selected = select_one(names, prompt="Delete profile")
    if not selected:
        return
    answer = input(f"Delete profile '{selected}'? [y/N] ").strip().lower()
    if answer not in ("y", "yes"):
        return
    delete_profile(selected)
    print(f"Deleted profile '{selected}'")


def cmd_profile(name: str | None = None) -> None:
    """Switch directly by name, or open the interactive profile menu."""
    if name:
        _switch(name)
        return

    active = active_profile()
    labels = [f"{item}{' *' if item == active else ''}" for item in profile_names()]
    save_label = "Save current setup..."
    delete_label = "Delete a profile..."
    exit_label = "Exit"
    selected = select_one([*labels, save_label, delete_label, exit_label], prompt="Profile")
    if not selected or selected == exit_label:
        return
    if selected == save_label:
        _save()
    elif selected == delete_label:
        _delete()
    else:
        _switch(selected.removesuffix(" *"))
