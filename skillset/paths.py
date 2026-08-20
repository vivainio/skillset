"""Path helpers and config-file I/O for skillset.

The on-disk config is YAML, loaded with ruamel.yaml in round-trip mode so
hand-written comments and structure survive tool edits.
"""

import os
import subprocess
import sys
from pathlib import Path

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedSeq

IS_WINDOWS = sys.platform == "win32"
IS_MACOS = sys.platform == "darwin"
CLAUDE_SETTINGS_FILE = ".claude/settings.json"
SKILLSET_CONFIG_FILE = "skillset.yaml"

_yaml = YAML(typ="rt")
_yaml.preserve_quotes = True
_yaml.default_flow_style = False
_yaml.indent(mapping=2, sequence=4, offset=2)


def get_cache_dir() -> Path:
    """Get the durable directory where repository sources are stored."""
    if IS_WINDOWS:
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    elif IS_MACOS:
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base / "skillset" / "repos"


def get_legacy_cache_dir() -> Path:
    """Get the former repository cache directory."""
    return Path.home() / ".cache" / "skillset" / "repos"


def get_repo_roots() -> list[Path]:
    """Return repository roots, preferring the durable location."""
    return [get_cache_dir(), get_legacy_cache_dir()]


def get_claude_home() -> Path:
    """Get the base Claude config directory.

    Honors CLAUDE_CONFIG_DIR (used to run multiple Claude Code profiles from
    one machine); falls back to ~/.claude.
    """
    override = os.environ.get("CLAUDE_CONFIG_DIR")
    return Path(override).expanduser() if override else Path.home() / ".claude"


def get_global_skills_dir() -> Path:
    """Get global Claude skills directory."""
    return get_claude_home() / "skills"


def ensure_global_skills_symlinks() -> list[Path]:
    """Link other agents' global skill directories to Claude's.

    Links are created only for agent directories that already exist. Existing
    non-empty skills paths and symlinks, including broken symlinks, are never
    overwritten. Codex's .system directory is moved under Claude's skills
    directory, then empty skills directories are replaced with links.
    """
    home = Path.home()
    candidates = [home / name for name in (".agents", ".codex", ".copilot")]
    parents = [path for path in candidates if path.is_dir()]
    target = get_global_skills_dir()
    created = []
    for parent in parents:
        link_path = parent / "skills"
        if link_path.is_symlink():
            continue
        try:
            system_dir = link_path / ".system"
            target_system_dir = target / ".system"
            if (
                parent.name == ".codex"
                and system_dir.is_dir()
                and not target_system_dir.is_symlink()
                and not target_system_dir.exists()
            ):
                target.mkdir(parents=True, exist_ok=True)
                system_dir.rename(target_system_dir)
            if link_path.is_dir():
                if any(link_path.iterdir()):
                    continue
                link_path.rmdir()
            elif link_path.exists():
                continue
            if IS_WINDOWS:
                subprocess.run(
                    ["cmd", "/c", "mklink", "/J", str(link_path), str(target)],
                    check=True,
                    capture_output=True,
                )
            else:
                link_path.symlink_to(target)
            created.append(link_path)
            print(f"Linked {abbrev(link_path)} -> {abbrev(target)}")
        except (OSError, subprocess.CalledProcessError):
            print(
                f"Could not link {abbrev(link_path)} -> {abbrev(target)} "
                "-- if this persists, retry from an admin shell."
            )
    return created


def get_git_root() -> Path | None:
    """Get the root of the current git repository, or None if not in one."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
        )
        return Path(result.stdout.strip())
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def get_main_worktree_root(cwd: Path | None = None) -> Path | None:
    """Get the root of the repo's main working tree, even from a linked worktree.

    `git rev-parse --git-common-dir` always points at the shared `.git`
    directory that lives inside the *main* worktree, regardless of which
    linked worktree it's invoked from (a linked worktree only has a `.git`
    file with a `gitdir:` pointer, not the real thing). Its parent is the
    main worktree's root. Returns None outside a git repo or for a bare repo.
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True,
        )
        common_dir = Path(result.stdout.strip())
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    return common_dir.parent if common_dir.name == ".git" else None


def resolve_editable_source(source_str: str, config_path: Path) -> Path:
    """Resolve a possibly-relative `source:` path from a skillset.yaml entry.

    Relative paths are anchored to the skillset.yaml's own directory, as
    normal. If that directory is a linked git worktree (e.g. a per-branch
    worktree checked out somewhere other than alongside its sibling repos),
    a sibling-relative path won't exist there even though it does next to
    the main worktree -- fall back to resolving against the main worktree's
    root in that case.
    """
    expanded = Path(source_str).expanduser()
    if expanded.is_absolute():
        return expanded.resolve()
    config_dir = config_path.parent
    primary = (config_dir / expanded).resolve()
    if primary.exists():
        return primary
    main_root = get_main_worktree_root(config_dir)
    if main_root is not None and main_root.resolve() != config_dir.resolve():
        fallback = (main_root / expanded).resolve()
        if fallback.exists():
            return fallback
    return primary


def get_project_skills_dir() -> Path | None:
    """Get project-local Claude skills directory, or None if not in a git repo."""
    root = get_git_root()
    return root / ".claude" / "skills" if root else None


def get_global_commands_dir() -> Path:
    """Get global Claude commands directory."""
    return get_claude_home() / "commands"


def get_global_agents_dir() -> Path:
    """Get global Claude agents directory."""
    return get_claude_home() / "agents"


def get_project_commands_dir() -> Path | None:
    """Get project-local Claude commands directory, or None if not in a git repo."""
    root = get_git_root()
    return root / ".claude" / "commands" if root else None


def get_project_agents_dir() -> Path | None:
    """Get project-local Claude agents directory, or None if not in a git repo."""
    root = get_git_root()
    return root / ".claude" / "agents" if root else None


def get_global_skillset_path() -> Path:
    """Get the path to the global skillset.yaml."""
    return get_claude_home() / SKILLSET_CONFIG_FILE


def get_profiles_path() -> Path:
    """Get the global profile configuration path."""
    return get_claude_home() / ".skillset" / "profiles.yaml"


def get_profile_store_dir() -> Path:
    """Get the private store for adopted unmanaged skills."""
    return get_claude_home() / ".skillset" / "skills"


def get_local_skillset_path() -> Path | None:
    """Get the path to the local skillset.yaml at the repo root, or None if not in a git repo."""
    root = get_git_root()
    return root / SKILLSET_CONFIG_FILE if root else None


def find_skillset_root() -> Path | None:
    """Walk up from CWD looking for skillset.yaml. Return its parent dir, or None."""
    current = Path.cwd()
    while True:
        if (current / SKILLSET_CONFIG_FILE).exists():
            return current
        parent = current.parent
        if parent == current:
            return None
        current = parent


def load_skillset(config_path: Path) -> dict:
    """Load a skillset.yaml file. Returns {} if missing or empty."""
    if not config_path.exists():
        return {}
    with config_path.open("r") as f:
        data = _yaml.load(f)
    return data or {}


def save_skillset(config_path: Path, data: object) -> None:
    """Write data back to a skillset.yaml file."""
    with config_path.open("w") as f:
        _yaml.dump(data, f)


def _flow_list(items: list[str]) -> CommentedSeq:
    """Build an inline (flow-style) YAML sequence for compact writes."""
    seq = CommentedSeq(items)
    seq.fa.set_flow_style()
    return seq


def add_to_skillset(  # noqa: C901
    config_path: Path,
    repo_key: str,
    *,
    path: str | None = None,
    enabled: list[str] | None = None,
    disabled: list[str] | None = None,
    agents: list[str] | None = None,
    editable: bool = False,
    source: str | None = None,
    ref: str | None = None,
    snapshot: bool = False,
) -> bool:
    """Add a new entry to a skillset.yaml file. Returns True if written.

    Skips silently if the file doesn't exist or the key is already registered.
    Skill selection is expressed as two lists:
      enabled: ["skill-a", "skill-b"]   # or ["*"] for all (supports globs)
      disabled: ["skill-c"]              # explicit opt-outs (skipped by update)
    """
    if not config_path.exists():
        return False

    data = load_skillset(config_path)
    skills = data.get("skills")
    if skills is None:
        skills = {}
        data["skills"] = skills
    if repo_key in skills:
        return False

    entry: dict = {}
    if editable:
        entry["editable"] = True
    if source:
        entry["source"] = source
    if path:
        entry["path"] = path
    if ref:
        entry["ref"] = ref
    if snapshot:
        entry["snapshot"] = True
    if enabled is not None:
        entry["enabled"] = _flow_list(enabled)
    if disabled:
        entry["disabled"] = _flow_list(disabled)
    if agents is not None:
        entry["agents"] = _flow_list(agents)

    skills[repo_key] = entry
    save_skillset(config_path, data)
    return True


def add_to_global_skillset(
    repo_key: str,
    *,
    path: str | None = None,
    enabled: list[str] | None = None,
    disabled: list[str] | None = None,
    editable: bool = False,
    source: str | None = None,
) -> bool:
    """Append a repo entry to ~/.claude/skillset.yaml if it exists. Returns True if written."""
    return add_to_skillset(
        get_global_skillset_path(),
        repo_key,
        path=path,
        enabled=enabled,
        disabled=disabled,
        editable=editable,
        source=source,
    )


def remove_from_skillset(config_path: Path, repo_key: str) -> bool:
    """Remove a repo entry from a skillset.yaml file. Returns True if removed."""
    if not config_path.exists():
        return False
    data = load_skillset(config_path)
    skills = data.get("skills")
    if not skills or repo_key not in skills:
        return False
    del skills[repo_key]
    save_skillset(config_path, data)
    return True


def update_skillset_skills(
    config_path: Path,
    repo_key: str,
    *,
    add_enabled: list[str] | None = None,
    add_disabled: list[str] | None = None,
) -> bool:
    """Fold skill names into the enabled/disabled lists of an existing entry.

    Move semantics: names added to `enabled` are removed from `disabled` and
    vice versa, so a skill is never listed in both. Dedupes within a list.
    Returns True if the file was modified.
    """
    add_enabled = add_enabled or []
    add_disabled = add_disabled or []
    if not config_path.exists() or not (add_enabled or add_disabled):
        return False

    data = load_skillset(config_path)
    skills = data.get("skills") or {}
    entry = skills.get(repo_key)
    if not isinstance(entry, dict):
        return False

    modified = False
    for name in add_enabled:
        modified |= _list_add(entry, "enabled", name)
        modified |= _list_remove(entry, "disabled", name)
    for name in add_disabled:
        modified |= _list_add(entry, "disabled", name)
        modified |= _list_remove(entry, "enabled", name)

    if modified:
        save_skillset(config_path, data)
    return modified


def set_skillset_agents(config_path: Path, repo_key: str, agents: list[str]) -> bool:
    """Replace an existing entry's flat agent selector list."""
    if not config_path.exists():
        return False
    data = load_skillset(config_path)
    entry = (data.get("skills") or {}).get(repo_key)
    if not isinstance(entry, dict):
        return False
    replacement = _flow_list(agents)
    if entry.get("agents") == replacement:
        return False
    entry["agents"] = replacement
    save_skillset(config_path, data)
    return True


def set_skillset_ref(config_path: Path, repo_key: str, ref: str | None) -> bool:
    """Set or clear the `ref:` field on an existing entry. Returns True if modified."""
    if not config_path.exists():
        return False
    data = load_skillset(config_path)
    entry = (data.get("skills") or {}).get(repo_key)
    if not isinstance(entry, dict):
        return False
    current = entry.get("ref")
    if ref == current:
        return False
    if ref is None:
        del entry["ref"]
    else:
        entry["ref"] = ref
    save_skillset(config_path, data)
    return True


def set_skillset_snapshot(config_path: Path, repo_key: str, snapshot: bool) -> bool:
    """Set or clear the `snapshot:` flag on an existing entry. Returns True if modified."""
    if not config_path.exists():
        return False
    data = load_skillset(config_path)
    entry = (data.get("skills") or {}).get(repo_key)
    if not isinstance(entry, dict):
        return False
    current = bool(entry.get("snapshot", False))
    if snapshot == current:
        return False
    if snapshot:
        entry["snapshot"] = True
    else:
        del entry["snapshot"]
    save_skillset(config_path, data)
    return True


def _list_add(entry: dict, key: str, name: str) -> bool:
    """Append name to entry[key]. Creates the list if missing. Dedupes."""
    items = entry.get(key)
    if items is None:
        entry[key] = _flow_list([name])
        return True
    if name in items:
        return False
    items.append(name)
    return True


def _list_remove(entry: dict, key: str, name: str) -> bool:
    """Remove name from entry[key] if present."""
    items = entry.get(key)
    if not items or name not in items:
        return False
    items.remove(name)
    return True


def require_project_dir(path: Path | None, kind: str = "project") -> Path:
    """Return path if set, or exit with error if not in a git repo."""
    if path is None:
        print(f"Not in a git repository — cannot use {kind} scope")
        sys.exit(1)
    return path


def abbrev(path: str | Path) -> str:
    """Replace the home directory prefix with `~`, wherever the path lives.

    An active CLAUDE_CONFIG_DIR profile is shown as its real absolute path
    (still `~`-shortened if it happens to live under the home directory)
    rather than as the `$CLAUDE_CONFIG_DIR` env var name -- the shorthand
    reads fine to whoever set the override, but is opaque to anyone else
    looking at the output.
    """
    s = str(path)
    home = str(Path.home())
    return s.replace(home, "~", 1) if s.startswith(home) else s
