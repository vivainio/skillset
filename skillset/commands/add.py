"""Command handlers for adding and initializing skills."""

import shutil
import sys
from pathlib import Path

from skillset.commands._resolve import _resolve_source, derive_toml_key_and_ref
from skillset.commands._templates import (
    GLOBAL_SKILLSET_TEMPLATE,
    LOCAL_SKILLSET_TEMPLATE,
)
from skillset.discovery import find_commands, find_skills
from skillset.linking import is_managed, link_commands, link_skills
from skillset.manifest import record_install
from skillset.paths import (
    SKILLSET_CONFIG_FILE,
    abbrev,
    add_to_skillset,
    find_skillset_root,
    get_cache_dir,
    get_global_commands_dir,
    get_global_skills_dir,
    get_global_skillset_path,
    get_local_skillset_path,
    load_skillset,
    set_skillset_ref,
    set_skillset_snapshot,
    update_skillset_skills,
)
from skillset.repo import get_head_sha
from skillset.ui import fzf_select, fzf_select_skills, prompt_skill_selection


def cmd_add(
    *,
    repo: str | None = None,
    g: bool = False,
    skills: list[str] | None = None,
    subpath: str | None = None,
    ref: str | None = None,
    copy: bool = False,
    no_cache: bool = False,
    trial: bool = False,
    interactive: bool = False,
    force: bool = False,
    snapshot: bool = False,
    unsnapshot: bool = False,
) -> None:
    """Add skills and permissions from a GitHub repo or local directory."""
    if snapshot and unsnapshot:
        print("--snapshot and --unsnapshot are mutually exclusive")
        sys.exit(1)

    skillset_root = None if g else find_skillset_root()
    is_local = skillset_root is not None

    # --snapshot: copy as-is, freeze in yaml; re-snapshotting overrides ref.
    if snapshot:
        copy = True
        force = True

    # --unsnapshot: drop the pinned ref + snapshot flag, switch back to live links.
    if unsnapshot:
        force = True
        ref = None

    if not _check_ref_conflict(repo, ref, is_local, skillset_root, force):
        return

    (
        repo,
        toml_key,
        toml_source,
        is_editable,
        repo_dir,
        temp_dir,
        source_label,
        skills,
        subpath,
        ref,
    ) = _resolve_source(repo, interactive, skills, subpath, no_cache, ref)
    if repo is None:
        return

    source_dir = repo_dir / subpath if subpath else repo_dir
    if subpath and not source_dir.is_dir():
        print(f"Path not found in repo: {subpath}")
        sys.exit(1)

    use_copy = copy or no_cache
    ref = _pin_snapshot_ref(snapshot, repo_dir, ref)

    skills_dir = (skillset_root / ".claude" / "skills") if is_local else get_global_skills_dir()

    linked_skills, enabled_list, disabled_list = _link_skills_for_add(
        source_dir, skills_dir, skills, interactive, use_copy, source_label
    )

    _print_linked("skill", linked_skills, use_copy, skills_dir)

    commands_dir = (
        (skillset_root / ".claude" / "commands") if is_local else get_global_commands_dir()
    )
    linked_commands = _link_commands_for_add(source_dir, commands_dir, interactive, use_copy)
    _print_linked("command", linked_commands, use_copy, commands_dir)

    if linked_skills or linked_commands:
        _record_install(repo_dir, subpath, use_copy, is_local, trial, skills)

    if toml_key and (linked_skills or linked_commands) and not trial:
        _ensure_toml_exists(is_editable, is_local, skillset_root)
        _register_in_toml(
            toml_key,
            subpath,
            enabled_list,
            disabled_list,
            is_editable,
            toml_source,
            is_local,
            skillset_root,
            ref,
            snapshot,
            unsnapshot,
        )

    if not linked_skills and not linked_commands:
        print("No skills found in repo")

    if temp_dir:
        shutil.rmtree(temp_dir, ignore_errors=True)


def _pin_snapshot_ref(snapshot: bool, repo_dir, ref):
    """For snapshot installs, replace ref with the resolved HEAD SHA."""
    if not snapshot or repo_dir is None:
        return ref
    return get_head_sha(repo_dir) or ref


def _link_skills_for_add(source_dir, skills_dir, skills, interactive, use_copy, source_label):
    """Select and link skills. Returns (linked_skills, enabled_list, disabled_list).

    enabled_list / disabled_list are what gets persisted to skillset.yaml:
      - enabled = ["*"] means "link everything in the repo"
      - explicit lists when the user picked a subset
      - (None, None) when there were no skills to link at all
    """
    skill_filter = set(skills) if skills else None

    if interactive:
        return _link_interactive_skills(source_dir, skills_dir, use_copy, source_label)

    if skill_filter is not None:
        available_skills = find_skills(source_dir)
        available_names = {s.name for s in available_skills}
        enabled = sorted(skill_filter & available_names)
        disabled = sorted(available_names - skill_filter)
        linked = link_skills(
            source_dir,
            skills_dir,
            only=skill_filter,
            copy=use_copy,
            source_label=source_label,
        )
        return linked, enabled, disabled

    return _link_prompted_skills(source_dir, skills_dir, use_copy, source_label)


def _link_interactive_skills(source_dir, skills_dir, use_copy, source_label):
    """Link skills selected via fzf. Returns (linked, enabled, disabled)."""
    available_skills = find_skills(source_dir)
    if not available_skills:
        return [], None, None
    installed = (
        {p.name for p in skills_dir.iterdir() if is_managed(p)} if skills_dir.exists() else set()
    )
    selected = set(fzf_select_skills(available_skills, source_dir, installed))
    available_names = {s.name for s in available_skills}
    enabled = sorted(selected & available_names)
    disabled = sorted(available_names - selected)
    linked = link_skills(
        source_dir,
        skills_dir,
        only=selected,
        copy=use_copy,
        source_label=source_label,
    )
    return linked, enabled, disabled


def _link_prompted_skills(source_dir, skills_dir, use_copy, source_label):
    """Link skills selected via interactive y/N prompt. Returns (linked, enabled, disabled)."""
    available_skills = find_skills(source_dir)
    if not available_skills:
        return [], None, None
    skill_filter, enabled, disabled = prompt_skill_selection(available_skills)
    linked = link_skills(
        source_dir,
        skills_dir,
        only=skill_filter,
        copy=use_copy,
        source_label=source_label,
    )
    return linked, enabled, disabled


def _link_commands_for_add(source_dir, commands_dir, interactive, use_copy):
    """Select and link commands. Returns linked command names."""
    if interactive:
        available_commands = find_commands(source_dir)
        if available_commands:
            cmd_names = sorted(c.name for c in available_commands)
            selected_cmds = fzf_select(cmd_names, prompt="Commands> ")
            return link_commands(source_dir, commands_dir, only=set(selected_cmds), copy=use_copy)
        return []
    return link_commands(source_dir, commands_dir, copy=use_copy)


def _print_linked(kind, linked, use_copy, target_dir):
    """Print linked skills/commands summary."""
    if linked:
        verb = "Copied" if use_copy else "Linked"
        print(f"{verb} {len(linked)} {kind}(s) to {abbrev(target_dir)}:")
        for name in sorted(linked):
            print(f"  - {name}")


def _record_install(repo_dir, subpath, use_copy, is_local, trial, skills):
    """Record install options in manifest."""
    try:
        rel = repo_dir.relative_to(get_cache_dir())
        repo_key = str(rel)
    except ValueError:
        repo_key = str(repo_dir)
    if trial:
        trial_value = True
    elif skills:
        trial_value = None
    else:
        trial_value = False
    record_install(
        repo_key,
        subpath=subpath,
        copy=use_copy,
        scope="local" if is_local else "global",
        trial=trial_value,
    )


def _ensure_toml_exists(is_editable, is_local, skillset_root):
    """Create skillset.yaml if missing and we're about to write to it.

    Only auto-creates for editable sources -- otherwise `add` should fail loudly
    when there's no config, to nudge the user toward `skillset init` first.
    """
    if not is_editable:
        return
    toml_path = (skillset_root / SKILLSET_CONFIG_FILE) if is_local else get_global_skillset_path()
    if not toml_path.exists():
        toml_path.parent.mkdir(parents=True, exist_ok=True)
        toml_path.write_text("skills: {}\n")


def _register_in_toml(
    toml_key,
    subpath,
    enabled,
    disabled,
    is_editable,
    toml_source,
    is_local,
    skillset_root,
    ref=None,
    snapshot=False,
    unsnapshot=False,
):
    """Register or update skillset.yaml entry for this repo."""
    toml_path = (skillset_root / SKILLSET_CONFIG_FILE) if is_local else get_global_skillset_path()

    written = add_to_skillset(
        toml_path,
        toml_key,
        path=subpath,
        enabled=enabled,
        disabled=disabled,
        editable=is_editable,
        source=toml_source,
        ref=ref,
        snapshot=snapshot,
    )
    if written:
        print(f"Added to {abbrev(toml_path)}")
        return

    # Repo already registered. --unsnapshot strips ref+snapshot; otherwise we
    # only rewrite ref when one was supplied. The --force conflict gate is
    # what allows reaching this branch with a different ref at all.
    if unsnapshot:
        if set_skillset_ref(toml_path, toml_key, None):
            print(f"Cleared ref in {abbrev(toml_path)}")
    elif ref is not None and set_skillset_ref(toml_path, toml_key, ref):
        print(f"Updated ref in {abbrev(toml_path)}")
    target_snapshot = False if unsnapshot else snapshot
    if set_skillset_snapshot(toml_path, toml_key, target_snapshot):
        state = "snapshot" if target_snapshot else "no-snapshot"
        print(f"Marked {toml_key} as {state} in {abbrev(toml_path)}")

    # Fold new selections into existing enabled list.
    # Newly-enabled names should also leave the disabled list if they were there.
    if enabled and "*" in enabled:
        return  # nothing sensible to fold when the user asked for "all"
    if not enabled:
        return
    updated = update_skillset_skills(
        toml_path,
        toml_key,
        add_enabled=enabled,
    )
    if updated:
        print(f"Updated {abbrev(toml_path)}")


def _check_ref_conflict(repo, ref, is_local, skillset_root, force) -> bool:
    """Refuse a ref override on an already-registered repo unless --force.

    Returns True to continue, False to abort cmd_add. When --force is set we
    only print a notice; the existing entry's ref is rewritten later.
    """
    toml_key, effective_ref = derive_toml_key_and_ref(repo, ref) if repo else (None, None)
    if not toml_key:
        return True

    toml_path = (skillset_root / SKILLSET_CONFIG_FILE) if is_local else get_global_skillset_path()
    if not toml_path.exists():
        return True

    data = load_skillset(toml_path)
    entry = (data.get("skills") or {}).get(toml_key)
    if not isinstance(entry, dict):
        return True

    existing_ref = entry.get("ref")
    if effective_ref == existing_ref:
        return True
    if existing_ref is None and effective_ref is None:
        return True

    new_label = effective_ref or "(none)"
    old_label = existing_ref or "(none)"
    if not force:
        print(
            f"{toml_key} is already pinned to ref {old_label} in "
            f"{abbrev(toml_path)}; refusing to install at {new_label}."
        )
        print("Edit skillset.yaml or re-run with --force to overwrite.")
        return False
    print(f"--force: overriding {toml_key} ref {old_label} -> {new_label}")
    return True


def cmd_init(*, g: bool = False) -> None:
    """Initialize a skillset.yaml file."""
    if g:
        path = get_global_skillset_path()
        template = GLOBAL_SKILLSET_TEMPLATE
    else:
        path = get_local_skillset_path()
        if path is None:
            print("Not in a git repository -- initializing in current directory")
            path = Path.cwd() / SKILLSET_CONFIG_FILE
        template = LOCAL_SKILLSET_TEMPLATE

    if path.exists():
        print(f"Already exists: {abbrev(path)}")
        sys.exit(1)

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(template)
    print(f"Created {abbrev(path)}")
