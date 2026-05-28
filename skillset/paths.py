"""Path helpers and config-file I/O for skillset.

The on-disk config is YAML, loaded with ruamel.yaml in round-trip mode so
hand-written comments and structure survive tool edits.
"""

import subprocess
import sys
from pathlib import Path

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedSeq

IS_WINDOWS = sys.platform == "win32"
CLAUDE_SETTINGS_FILE = ".claude/settings.json"
SKILLSET_CONFIG_FILE = "skillset.yaml"

_yaml = YAML(typ="rt")
_yaml.preserve_quotes = True
_yaml.default_flow_style = False
_yaml.indent(mapping=2, sequence=4, offset=2)


def get_cache_dir() -> Path:
    """Get the directory where repos are cached."""
    return Path.home() / ".cache" / "skillset" / "repos"


def get_global_skills_dir() -> Path:
    """Get global Claude skills directory."""
    return Path.home() / ".claude" / "skills"


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


def get_project_skills_dir() -> Path | None:
    """Get project-local Claude skills directory, or None if not in a git repo."""
    root = get_git_root()
    return root / ".claude" / "skills" if root else None


def get_global_commands_dir() -> Path:
    """Get global Claude commands directory."""
    return Path.home() / ".claude" / "commands"


def get_project_commands_dir() -> Path | None:
    """Get project-local Claude commands directory, or None if not in a git repo."""
    root = get_git_root()
    return root / ".claude" / "commands" if root else None


def get_global_skillset_path() -> Path:
    """Get the path to the global skillset.yaml."""
    return Path.home() / ".claude" / SKILLSET_CONFIG_FILE


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


def save_skillset(config_path: Path, data) -> None:
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
    """Replace home directory with ~ in a path string."""
    s = str(path)
    home = str(Path.home())
    return s.replace(home, "~", 1) if s.startswith(home) else s
