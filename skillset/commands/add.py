"""Command handlers for adding and initializing skills."""

import fnmatch
import shutil
import sys
from collections.abc import Callable
from pathlib import Path

from skillset.commands._resolve import _resolve_source, derive_toml_key_and_ref
from skillset.commands._templates import (
    GLOBAL_SKILLSET_TEMPLATE,
    LOCAL_SKILLSET_TEMPLATE,
)
from skillset.discovery import find_agents, find_commands, find_skills
from skillset.linking import (
    has_glob,
    is_managed,
    link_agents,
    link_commands,
    link_skills,
    normalize_glob,
    remove_unselected_agents,
    remove_unselected_commands,
)
from skillset.manifest import record_install
from skillset.paths import (
    SKILLSET_CONFIG_FILE,
    abbrev,
    add_to_skillset,
    ensure_global_skills_symlinks,
    find_skillset_root,
    get_global_agents_dir,
    get_global_commands_dir,
    get_global_skills_dir,
    get_global_skillset_path,
    get_local_skillset_path,
    get_repo_roots,
    load_skillset,
    resolve_editable_source,
    set_skillset_agents,
    set_skillset_commands,
    set_skillset_ref,
    set_skillset_snapshot,
    update_skillset_skills,
)
from skillset.repo import get_head_sha
from skillset.ui import fzf_select, fzf_select_skills, prompt_skill_selection

SkillSelectionResult = tuple[list[str], list[str] | None, list[str] | None]
AgentSelectionResult = tuple[list[str], list[str] | None]
CommandSelectionResult = tuple[list[str], list[str] | None]


def cmd_add(
    *,
    repo: str | None = None,
    g: bool = False,
    skills: list[str] | None = None,
    agents: list[str] | None = None,
    commands: list[str] | None = None,
    subpath: str | None = None,
    ref: str | None = None,
    copy: bool = False,
    no_cache: bool = False,
    trial: bool = False,
    interactive: bool = False,
    force: bool = False,
    snapshot: bool = False,
    unsnapshot: bool = False,
    fetch: bool = False,
) -> None:
    """Add skills and permissions from a GitHub repo or local directory."""
    copy, force, ref = _apply_snapshot_flags(snapshot, unsnapshot, copy, force, ref)

    skillset_root = None if g else find_skillset_root()
    is_local = skillset_root is not None

    if not _check_ref_conflict(repo, ref, is_local, skillset_root, force):
        return

    resolved = _resolve_source(repo, interactive, skills, subpath, no_cache, ref)
    if resolved is None:
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
    ) = resolved

    toml_key, toml_source = _reuse_registered_editable(
        repo_dir,
        toml_key,
        toml_source,
        is_editable,
        is_local,
        skillset_root,
    )

    source_dir = repo_dir / subpath if subpath else repo_dir
    if subpath and not source_dir.is_dir():
        print(f"Path not found in repo: {subpath}")
        sys.exit(1)

    if fetch:
        _do_fetch(
            repo_dir,
            source_dir,
            temp_dir,
            toml_key,
            toml_source,
            subpath,
            is_editable,
            is_local,
            skillset_root,
            ref,
            snapshot,
            unsnapshot,
            trial,
        )
        return

    use_copy = copy or no_cache
    ref = _pin_snapshot_ref(snapshot, repo_dir, ref)

    skills_dir = (skillset_root / ".claude" / "skills") if is_local else get_global_skills_dir()

    linked_skills, enabled_list, disabled_list = _link_skills_for_add(
        source_dir, skills_dir, skills, interactive, use_copy, source_label
    )

    _print_linked("skill", linked_skills, use_copy, skills_dir)

    if not is_local and linked_skills:
        ensure_global_skills_symlinks()

    commands_dir = (
        (skillset_root / ".claude" / "commands") if is_local else get_global_commands_dir()
    )
    linked_commands, command_selectors = _link_commands_for_add(
        source_dir, commands_dir, commands, interactive, use_copy
    )
    _remove_unselected_for_explicit_filter(
        remove_unselected_commands, source_dir, commands_dir, linked_commands, command_selectors
    )
    _print_linked("command", linked_commands, use_copy, commands_dir)

    agents_dir = (skillset_root / ".claude" / "agents") if is_local else get_global_agents_dir()
    linked_agents, agent_selectors = _link_agents_for_add(
        source_dir, agents_dir, agents, interactive, use_copy
    )
    _remove_unselected_for_explicit_filter(
        remove_unselected_agents, source_dir, agents_dir, linked_agents, agent_selectors
    )
    _print_linked("agent", linked_agents, use_copy, agents_dir)

    linked_any = linked_skills or linked_commands or linked_agents
    if toml_key and linked_any:
        _record_install(repo_dir, subpath, use_copy, is_local, trial, skills)

    if toml_key and linked_any and not trial:
        _ensure_toml_exists(is_editable, is_local, skillset_root)
        _register_in_toml(
            toml_key,
            subpath,
            enabled_list,
            disabled_list,
            agent_selectors,
            command_selectors,
            is_editable,
            toml_source,
            is_local,
            skillset_root,
            ref,
            snapshot,
            unsnapshot,
        )

    if not linked_any:
        print("No skills found in repo (and no commands or agents)")

    if temp_dir:
        shutil.rmtree(temp_dir, ignore_errors=True)


def _do_fetch(
    repo_dir: Path,
    source_dir: Path,
    temp_dir: Path | None,
    toml_key: str | None,
    toml_source: str | None,
    subpath: str | None,
    is_editable: bool,
    is_local: bool,
    skillset_root: Path | None,
    ref: str | None,
    snapshot: bool,
    unsnapshot: bool,
    trial: bool,
) -> None:
    """Clone/cache the repo and register it with no skills enabled -- link nothing."""
    print(f"Fetched {abbrev(repo_dir)}")
    if toml_key and not trial:
        available = find_skills(source_dir)
        disabled = sorted(s.name for s in available)
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
            snapshot,
            unsnapshot,
        )
    if temp_dir:
        shutil.rmtree(temp_dir, ignore_errors=True)


def _apply_snapshot_flags(
    snapshot: bool, unsnapshot: bool, copy: bool, force: bool, ref: str | None
) -> tuple[bool, bool, str | None]:
    """Resolve --snapshot / --unsnapshot into (copy, force, ref) adjustments.

    --snapshot: copy as-is and freeze in yaml; re-snapshotting overrides ref.
    --unsnapshot: drop the pinned ref + snapshot flag, switch back to live links.
    """
    if snapshot and unsnapshot:
        print("--snapshot and --unsnapshot are mutually exclusive")
        sys.exit(1)
    if snapshot:
        copy = True
        force = True
    if unsnapshot:
        force = True
        ref = None
    return copy, force, ref


def _pin_snapshot_ref(snapshot: bool, repo_dir: Path, ref: str | None) -> str | None:
    """For snapshot installs, replace ref with the resolved HEAD SHA."""
    if not snapshot or repo_dir is None:
        return ref
    return get_head_sha(repo_dir) or ref


def _link_skills_for_add(
    source_dir: Path,
    skills_dir: Path,
    skills: list[str] | None,
    interactive: bool,
    use_copy: bool,
    source_label: str | None,
) -> SkillSelectionResult:
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
        # Persist glob patterns as patterns (canonical `*` form) so `update`
        # re-expands them and picks up new matching skills later; literals are
        # stored verbatim. Disabled = everything not selected by either.
        patterns = {normalize_glob(n) for n in skill_filter if has_glob(n)}
        literals = {n for n in skill_filter if not has_glob(n)}
        matched = {n for n in available_names if any(fnmatch.fnmatch(n, p) for p in patterns)}
        selected = (literals & available_names) | matched
        enabled = sorted((literals & available_names) | patterns)
        disabled = sorted(available_names - selected)
        linked = link_skills(
            source_dir,
            skills_dir,
            only=skill_filter,
            copy=use_copy,
            source_label=source_label,
        )
        return linked, enabled, disabled

    return _link_prompted_skills(source_dir, skills_dir, use_copy, source_label)


def _link_interactive_skills(
    source_dir: Path, skills_dir: Path, use_copy: bool, source_label: str | None
) -> SkillSelectionResult:
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


def _link_prompted_skills(
    source_dir: Path, skills_dir: Path, use_copy: bool, source_label: str | None
) -> SkillSelectionResult:
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


def _link_commands_for_add(
    source_dir: Path,
    commands_dir: Path,
    commands: list[str] | None,
    interactive: bool,
    use_copy: bool,
) -> CommandSelectionResult:
    """Select and link commands, returning linked names and persisted selectors."""
    if interactive:
        available_commands = find_commands(source_dir)
        if not available_commands:
            return [], None
        cmd_names = sorted(c.name.removesuffix(".md") for c in available_commands)
        selected = set(fzf_select(cmd_names, prompt="Commands> "))
        only = {f"{name}.md" for name in selected}
        return link_commands(source_dir, commands_dir, only=only, copy=use_copy), sorted(selected)

    if commands is None:
        return link_commands(source_dir, commands_dir, copy=use_copy), None

    available = {c.name.removesuffix(".md") for c in find_commands(source_dir)}
    patterns = {normalize_glob(name) for name in commands if has_glob(name)}
    literals = {name.removesuffix(".md") for name in commands if not has_glob(name)}
    matched = {name for name in available if any(fnmatch.fnmatch(name, p) for p in patterns)}
    selected = (literals & available) | matched
    for name in sorted(literals - available):
        print(f"  Command '{name}' not found")
    for pattern in sorted(patterns):
        if not any(fnmatch.fnmatch(name, pattern) for name in available):
            print(f"  Pattern '{pattern}' matched no commands")
    only = {f"{name}.md" for name in selected}
    enabled = sorted((literals & available) | patterns)
    return link_commands(source_dir, commands_dir, only=only, copy=use_copy), enabled


def _agent_names(source_dir: Path) -> set[str]:
    """Return install-relative agent names without the Markdown suffix."""
    return {relative.with_suffix("").as_posix() for _, relative in find_agents(source_dir)}


def _remove_unselected_for_explicit_filter(
    remove_fn: Callable[[Path, Path, set[str]], None],
    source_dir: Path,
    target_dir: Path,
    linked: list[str],
    selectors: list[str] | None,
) -> None:
    """Apply replacement semantics only when an explicit filter was supplied."""
    if selectors is not None:
        remove_fn(source_dir, target_dir, set(linked))


def _link_agents_for_add(
    source_dir: Path,
    agents_dir: Path,
    agents: list[str] | None,
    interactive: bool,
    use_copy: bool,
) -> AgentSelectionResult:
    """Select and link agents, returning linked names and persisted selectors."""
    available = _agent_names(source_dir)
    if interactive:
        if not available:
            return [], None
        selected = set(fzf_select(sorted(available), prompt="Agents> "))
        return (
            link_agents(source_dir, agents_dir, only=selected, copy=use_copy),
            sorted(selected),
        )
    if agents is None:
        return link_agents(source_dir, agents_dir, copy=use_copy), None

    patterns = {normalize_glob(name) for name in agents if has_glob(name)}
    literals = {name.removesuffix(".md") for name in agents if not has_glob(name)}
    matched = {name for name in available if any(fnmatch.fnmatch(name, p) for p in patterns)}
    selected = (literals & available) | matched
    for name in sorted(literals - available):
        print(f"  Agent '{name}' not found")
    for pattern in sorted(patterns):
        if not any(fnmatch.fnmatch(name, pattern) for name in available):
            print(f"  Pattern '{pattern}' matched no agents")
    enabled = sorted((literals & available) | patterns)
    return (
        link_agents(source_dir, agents_dir, only=selected, copy=use_copy),
        enabled,
    )


def _print_linked(kind: str, linked: list[str], use_copy: bool, target_dir: Path) -> None:
    """Print linked skills/commands summary."""
    if linked:
        verb = "Copied" if use_copy else "Linked"
        print(f"{verb} {len(linked)} {kind}(s) to {abbrev(target_dir)}:")
        for name in sorted(linked):
            print(f"  - {name}")


def _record_install(
    repo_dir: Path,
    subpath: str | None,
    use_copy: bool,
    is_local: bool,
    trial: bool,
    skills: list[str] | None,
) -> None:
    """Record install options in manifest."""
    repo_key = str(repo_dir)
    for root in get_repo_roots():
        try:
            repo_key = str(repo_dir.relative_to(root))
            break
        except ValueError:
            continue
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


def _ensure_toml_exists(is_editable: bool, is_local: bool, skillset_root: Path | None) -> None:
    """Create skillset.yaml if missing and we're about to write to it.

    Only auto-creates for editable sources -- otherwise `add` should fail loudly
    when there's no config, to nudge the user toward `skillset init` first.
    """
    if not is_editable:
        return
    if is_local:
        assert skillset_root is not None
        toml_path = skillset_root / SKILLSET_CONFIG_FILE
    else:
        toml_path = get_global_skillset_path()
    if not toml_path.exists():
        toml_path.parent.mkdir(parents=True, exist_ok=True)
        toml_path.write_text("skills: {}\n")


def _reuse_registered_editable(
    repo_dir: Path,
    toml_key: str | None,
    toml_source: str | None,
    is_editable: bool,
    is_local: bool,
    skillset_root: Path | None,
) -> tuple[str | None, str | None]:
    """Reuse the most specific registered editable source containing repo_dir."""
    if not is_editable:
        return toml_key, toml_source
    if is_local:
        assert skillset_root is not None
        toml_path = skillset_root / SKILLSET_CONFIG_FILE
    else:
        toml_path = get_global_skillset_path()
    if not toml_path.exists():
        return toml_key, toml_source
    matches = []
    for key, entry in (load_skillset(toml_path).get("skills") or {}).items():
        if not isinstance(entry, dict) or not entry.get("editable") or not entry.get("source"):
            continue
        source = resolve_editable_source(entry["source"], toml_path)
        try:
            repo_dir.resolve().relative_to(source)
        except ValueError:
            continue
        matches.append((len(source.parts), key, entry["source"]))
    if not matches:
        return toml_key, toml_source
    _, key, source = max(matches)
    return key, source


def _register_in_toml(
    toml_key: str,
    subpath: str | None,
    enabled: list[str] | None,
    disabled: list[str] | None,
    agents: list[str] | None,
    commands: list[str] | None,
    is_editable: bool,
    toml_source: str | None,
    is_local: bool,
    skillset_root: Path | None,
    ref: str | None = None,
    snapshot: bool = False,
    unsnapshot: bool = False,
) -> None:
    """Register or update skillset.yaml entry for this repo."""
    if is_local:
        assert skillset_root is not None
        toml_path = skillset_root / SKILLSET_CONFIG_FILE
    else:
        toml_path = get_global_skillset_path()

    written = add_to_skillset(
        toml_path,
        toml_key,
        path=subpath,
        enabled=enabled,
        disabled=disabled,
        agents=agents,
        commands=commands,
        editable=is_editable,
        source=toml_source,
        ref=ref,
        snapshot=snapshot,
    )
    if written:
        print(f"Added to {abbrev(toml_path)}")
        return

    _update_existing_registration(
        toml_path, toml_key, enabled, agents, commands, ref, snapshot, unsnapshot
    )


def _update_existing_registration(
    toml_path: Path,
    toml_key: str,
    enabled: list[str] | None,
    agents: list[str] | None,
    commands: list[str] | None,
    ref: str | None,
    snapshot: bool,
    unsnapshot: bool,
) -> None:
    """Amend an already-registered skillset.yaml entry: ref/snapshot state and selections."""
    # --unsnapshot strips ref+snapshot; otherwise we only rewrite ref when one
    # was supplied. The --force conflict gate is what allows reaching this
    # function with a different ref at all.
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
    updated = False
    if enabled and "*" not in enabled:
        updated |= update_skillset_skills(toml_path, toml_key, add_enabled=enabled)
    if agents is not None:
        updated |= set_skillset_agents(toml_path, toml_key, agents)
    if commands is not None:
        updated |= set_skillset_commands(toml_path, toml_key, commands)
    if updated:
        print(f"Updated {abbrev(toml_path)}")


def _check_ref_conflict(
    repo: str | None,
    ref: str | None,
    is_local: bool,
    skillset_root: Path | None,
    force: bool,
) -> bool:
    """Refuse a ref override on an already-registered repo unless --force.

    Returns True to continue, False to abort cmd_add. When --force is set we
    only print a notice; the existing entry's ref is rewritten later.
    """
    toml_key, effective_ref = derive_toml_key_and_ref(repo, ref) if repo else (None, None)
    if not toml_key:
        return True

    if is_local:
        assert skillset_root is not None
        toml_path = skillset_root / SKILLSET_CONFIG_FILE
    else:
        toml_path = get_global_skillset_path()
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
