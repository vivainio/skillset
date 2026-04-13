"""CLI for managing AI skills and permissions across projects."""

import argparse
import difflib
import fnmatch
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from skillset.builtins import PRESETS as BUILTIN_PRESETS

IS_WINDOWS = sys.platform == "win32"
CLAUDE_SETTINGS_FILE = ".claude/settings.json"



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
            capture_output=True, text=True, check=True,
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


def get_global_settings_path() -> Path:
    """Get global Claude settings.local path (user preferences)."""
    return Path.home() / ".claude" / "settings.local.json"


def get_project_settings_path() -> Path | None:
    """Get project-local Claude settings.local path, or None if not in a git repo."""
    root = get_git_root()
    return root / ".claude" / "settings.local.json" if root else None


def require_project_dir(path: Path | None, kind: str = "project") -> Path:
    """Return path if set, or exit with error if not in a git repo."""
    if path is None:
        print(f"Not in a git repository — cannot use {kind} scope")
        sys.exit(1)
    return path


def parse_repo_spec(spec: str) -> tuple[str, str]:
    """Parse 'owner/repo' into (owner, repo)."""
    parts = spec.strip().split("/")
    if len(parts) != 2:
        raise ValueError(f"Invalid repo format: {spec}. Use 'owner/repo'")
    return parts[0], parts[1]


def parse_github_url(url: str) -> tuple[str, str, str | None, str | None] | None:
    """Parse a GitHub tree URL into (owner, repo, branch, subpath) or None.

    Handles:
      https://github.com/owner/repo
      https://github.com/owner/repo/tree/branch/path/to/subdir
    """
    import re
    m = re.match(r'https?://github\.com/([^/]+)/([^/]+)(?:/tree/([^/]+)(?:/(.+))?)?/?$', url)
    if not m:
        return None
    return m.group(1), m.group(2).removesuffix(".git"), m.group(3), m.group(4)


def get_repo_dir(owner: str, repo: str) -> Path:
    """Get the cache directory for a repo."""
    return get_cache_dir() / owner / repo


def get_manifest_path() -> Path:
    """Get the path to the install manifest."""
    return get_cache_dir() / "manifest.json"


def load_manifest() -> dict:
    """Load the install manifest (tracks per-repo install options)."""
    path = get_manifest_path()
    if path.exists():
        return json.loads(path.read_text())
    return {}


def save_manifest(manifest: dict) -> None:
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
    skills: list[str] | None = None,
    commands: list[str] | None = None,
    replace_items: bool = False,
) -> None:
    """Record install options for a repo in the manifest.

    trial=True/False explicitly sets the flag; trial=None preserves the existing value.
    skills/commands: names linked from this repo. By default they are merged with
    any previously recorded list; pass replace_items=True to overwrite.
    """
    manifest = load_manifest()
    existing = manifest.get(repo_key, {})

    def _merge(new_items: list[str] | None, key: str) -> list[str]:
        prev = list(existing.get(key, []))
        if new_items is None:
            return prev
        if replace_items:
            return sorted(set(new_items))
        return sorted(set(prev) | set(new_items))

    entry = {
        "subpath": subpath,
        "copy": copy,
        "scope": scope,
        "trial": existing.get("trial", False) if trial is None else trial,
        "skills": _merge(skills, "skills"),
        "commands": _merge(commands, "commands"),
    }
    manifest[repo_key] = entry
    save_manifest(manifest)


def get_install_options(repo_key: str) -> dict | None:
    """Get saved install options for a repo."""
    return load_manifest().get(repo_key)


def clone_or_pull(owner: str, repo: str) -> Path:
    """Clone repo if not exists, or pull if it does. Returns repo path."""
    repo_dir = get_repo_dir(owner, repo)
    https_url = f"https://github.com/{owner}/{repo}.git"
    ssh_url = f"git@github.com:{owner}/{repo}.git"

    if repo_dir.exists():
        print(f"Updating {owner}/{repo}...")
        try:
            subprocess.run(["git", "pull"], cwd=repo_dir, check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            stderr = e.stderr.decode() if e.stderr else ""
            stdout = e.stdout.decode() if e.stdout else ""
            msg = stderr or stdout or "(no output)"
            print(f"Warning: git pull failed in {repo_dir}:\n{msg}")
    else:
        print(f"Cloning {owner}/{repo}...")
        repo_dir.parent.mkdir(parents=True, exist_ok=True)
        try:
            subprocess.run(
                ["git", "clone", https_url, str(repo_dir)], check=True, capture_output=True
            )
        except subprocess.CalledProcessError as e:
            # If HTTPS fails (e.g., auth failed for private repo), try SSH
            stderr = e.stderr.decode() if e.stderr else ""
            if "Authentication failed" in stderr or e.returncode == 128:
                print(f"HTTPS failed, trying SSH...")
                subprocess.run(
                    ["git", "clone", ssh_url, str(repo_dir)], check=True, capture_output=True
                )
            else:
                raise

    return repo_dir


def clone_to_temp(owner: str, repo: str) -> Path:
    """Clone repo to a temp directory (caller must clean up). Returns repo path."""
    tmp_dir = Path(tempfile.mkdtemp(prefix="skillset-"))
    repo_dir = tmp_dir / repo
    https_url = f"https://github.com/{owner}/{repo}.git"
    ssh_url = f"git@github.com:{owner}/{repo}.git"

    print(f"Cloning {owner}/{repo} (no-cache)...")
    try:
        subprocess.run(
            ["git", "clone", "--depth", "1", https_url, str(repo_dir)],
            check=True, capture_output=True,
        )
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode() if e.stderr else ""
        if "Authentication failed" in stderr or e.returncode == 128:
            print(f"HTTPS failed, trying SSH...")
            subprocess.run(
                ["git", "clone", "--depth", "1", ssh_url, str(repo_dir)],
                check=True, capture_output=True,
            )
        else:
            raise
    return repo_dir


def find_skills(repo_dir: Path) -> list[Path]:
    """Find skill directories in a repo. A skill is a dir containing SKILL.md."""
    skills = []
    for skill_file in repo_dir.glob("**/SKILL.md"):
        if any(part.startswith(".") for part in skill_file.relative_to(repo_dir).parts):
            continue
        skill_dir = skill_file.parent
        if skill_dir not in skills:
            skills.append(skill_dir)
    return skills


def find_commands(repo_dir: Path) -> list[Path]:
    """Find command files in a repo. Commands are .md files in commands/ directories (nested ok)."""
    commands = []
    for cmd_file in repo_dir.glob("**/commands/**/*.md"):
        if any(part.startswith(".") for part in cmd_file.relative_to(repo_dir).parts):
            continue
        commands.append(cmd_file)
    # Also check direct children of commands/
    for cmd_file in repo_dir.glob("**/commands/*.md"):
        if any(part.startswith(".") for part in cmd_file.relative_to(repo_dir).parts):
            continue
        if cmd_file not in commands:
            commands.append(cmd_file)
    return commands


def create_dir_link(link_path: Path, target_path: Path) -> None:
    """Create a directory link (junction on Windows, symlink on Unix)."""
    if IS_WINDOWS:
        # Use junction on Windows (no admin required)
        subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(link_path), str(target_path)],
            check=True,
            capture_output=True,
        )
    else:
        link_path.symlink_to(target_path)


def is_link(path: Path) -> bool:
    """Check if path is a symlink or junction."""
    if IS_WINDOWS:
        # Junctions have the reparse-point attribute but don't always report as
        # symlinks. Check st_file_attributes directly.
        try:
            st = path.lstat()
        except (OSError, ValueError):
            return False
        FILE_ATTRIBUTE_REPARSE_POINT = 0x400
        return bool(getattr(st, "st_file_attributes", 0) & FILE_ATTRIBUTE_REPARSE_POINT)
    return path.is_symlink()


def remove_link(path: Path) -> None:
    """Remove a symlink or junction."""
    if IS_WINDOWS and path.is_dir():
        # Junctions need rmdir, not unlink
        os.rmdir(path)
    else:
        path.unlink()


SKILLSET_SOURCE_MARKER = ".skillset-source"


def fuzzy_match(name: str, candidates: list[str], cutoff: float = 0.6) -> str | None:
    """Find the best fuzzy match for name among candidates."""
    matches = difflib.get_close_matches(name, candidates, n=1, cutoff=cutoff)
    return matches[0] if matches else None


def is_managed_copy(path: Path) -> bool:
    """Check if path is a skillset-managed copy (has marker file)."""
    return path.is_dir() and (path / SKILLSET_SOURCE_MARKER).is_file()


def get_copy_source(path: Path) -> str | None:
    """Get the source path from a managed copy's marker file."""
    marker = path / SKILLSET_SOURCE_MARKER
    if marker.is_file():
        return marker.read_text().strip()
    return None


def is_managed(path: Path) -> bool:
    """Check if path is managed by skillset (link or copy)."""
    return is_link(path) or is_managed_copy(path)


def remove_managed(path: Path) -> None:
    """Remove a managed skill (link or copy)."""
    if is_link(path):
        remove_link(path)
    elif is_managed_copy(path):
        shutil.rmtree(path)
    else:
        raise ValueError(f"Not a managed path: {path}")


def copy_dir(src: Path, dst: Path, source_label: str | None = None) -> None:
    """Copy a directory and write a marker file recording the source."""
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    (dst / SKILLSET_SOURCE_MARKER).write_text((source_label or str(src)) + "\n")


def link_skills(repo_dir: Path, target_dir: Path, only: set[str] | None = None, copy: bool = False, source_label: str | None = None, existing_only: bool = False) -> list[str]:
    """Link (or copy) skill directories from repo to target skills dir."""
    target_dir.mkdir(parents=True, exist_ok=True)
    available = find_skills(repo_dir)
    available_names = [s.name for s in available]

    # When existing_only, restrict to skills already present in target dir
    if existing_only:
        existing = {p.name for p in target_dir.iterdir() if p.is_dir() or p.is_symlink()}
        if only is not None:
            only = only & existing
        else:
            only = existing

    # Resolve requested names: expand glob patterns, fuzzy-match typos
    if only is not None:
        verified = set()
        for name in only:
            if any(c in name for c in "*?["):
                # Glob pattern — expand against available names
                matched = fnmatch.filter(available_names, name)
                if matched:
                    verified.update(matched)
                else:
                    print(f"  Pattern '{name}' matched no skills")
            elif name in available_names:
                verified.add(name)
            else:
                suggestion = fuzzy_match(name, available_names)
                if suggestion:
                    print(f"  Skill '{name}' not found. Did you mean '{suggestion}'?")
                else:
                    print(f"  Skill '{name}' not found (no close match)")
        only = verified

    linked = []
    for skill_dir in available:
        skill_name = skill_dir.name
        if only is not None and skill_name not in only:
            continue
        link_path = target_dir / skill_name
        if is_managed(link_path):
            remove_managed(link_path)
        elif link_path.exists():
            print(f"  Skipping {skill_name}: already exists (not managed by skillset)")
            continue
        if copy:
            copy_dir(skill_dir, link_path, source_label=source_label)
        else:
            create_dir_link(link_path, skill_dir)
        linked.append(skill_name)
    return linked


def link_commands(repo_dir: Path, target_dir: Path, only: set[str] | None = None, copy: bool = False, existing_only: bool = False) -> list[str]:
    """Link (or copy) command files from repo to target commands dir."""
    target_dir.mkdir(parents=True, exist_ok=True)
    if existing_only:
        existing = {p.name for p in target_dir.iterdir() if p.is_file() or p.is_symlink()}
        if only is not None:
            only = only & existing
        else:
            only = existing
    linked = []
    for cmd_file in find_commands(repo_dir):
        cmd_name = cmd_file.name
        if only is not None and cmd_name not in only:
            continue
        link_path = target_dir / cmd_name
        if link_path.is_symlink():
            link_path.unlink()
        elif link_path.exists():
            if copy:
                link_path.unlink()
            else:
                print(f"  Skipping {cmd_name}: already exists (not a link)")
                continue
        if copy:
            shutil.copy2(cmd_file, link_path)
        else:
            link_path.symlink_to(cmd_file)
        linked.append(cmd_name)
    return linked


def load_settings(settings_path: Path) -> dict:
    """Load Claude settings from a path."""
    if settings_path.exists():
        return json.loads(settings_path.read_text())
    return {}


def save_settings(settings_path: Path, settings: dict) -> None:
    """Save Claude settings to a path."""
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(json.dumps(settings, indent=2) + "\n")


def find_repo_permissions(repo_dir: Path) -> dict | None:
    """Find and load permissions file from repo root."""
    for name in ("settings.json", "permissions.json", "claude-settings.json"):
        path = repo_dir / name
        if path.exists():
            return json.loads(path.read_text())
    return None


def deep_merge(base: dict, override: dict) -> dict:
    """Deep merge two dictionaries, with override taking precedence."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        elif key in result and isinstance(result[key], list) and isinstance(value, list):
            result[key] = list(set(result[key] + value))
        else:
            result[key] = value
    return result


def merge_permissions(repo_dir: Path, settings_path: Path) -> list[str]:
    """Merge repo permissions into target settings."""
    repo_perms = find_repo_permissions(repo_dir)
    if not repo_perms:
        return []
    existing = load_settings(settings_path)
    merged = deep_merge(existing, repo_perms)
    save_settings(settings_path, merged)
    return list(repo_perms.keys())


def get_preset(name: str) -> dict | None:
    """Get a preset by name."""
    return BUILTIN_PRESETS.get(name)


def abbrev(path: str | Path) -> str:
    """Replace home directory with ~ in a path string."""
    s = str(path)
    home = str(Path.home())
    return s.replace(home, "~", 1) if s.startswith(home) else s


# Command handlers


def cmd_list(args: argparse.Namespace) -> None:
    """List installed skills and commands."""
    prune = getattr(args, "prune", False)
    global_skills_dir = get_global_skills_dir()
    project_skills_dir = get_project_skills_dir()
    global_commands_dir = get_global_commands_dir()
    project_commands_dir = get_project_commands_dir()

    global_skills = sorted(global_skills_dir.iterdir()) if global_skills_dir.exists() else []
    if project_skills_dir and project_skills_dir.exists():
        project_skills = sorted(project_skills_dir.iterdir())
    else:
        project_skills = []
    global_commands = sorted(global_commands_dir.iterdir()) if global_commands_dir.exists() else []
    if project_commands_dir and project_commands_dir.exists():
        project_commands = sorted(project_commands_dir.iterdir())
    else:
        project_commands = []

    # Build set of trial repo keys for tagging
    manifest = load_manifest()
    trial_repos = {k for k, v in manifest.items() if v.get("trial")}

    def _is_trial_skill(item: Path) -> bool:
        """Check if a skill belongs to a trial repo."""
        if is_managed_copy(item):
            source = get_copy_source(item) or ""
        elif is_link(item):
            resolved = item.resolve()
            source = str(resolved.parent)
        else:
            return False
        # Match against trial repo keys (which may be owner/repo or absolute paths)
        for key in trial_repos:
            if key in source or abbrev(key) in abbrev(source):
                return True
        return False

    def print_grouped(items: list[Path], is_link_fn, label: str, install_dir: Path) -> None:
        if not items:
            return
        print(f"{label} ({abbrev(install_dir)}):")
        groups: dict[str, list[str]] = {}
        broken: list[Path] = []
        for item in items:
            if is_link_fn(item):
                if is_managed_copy(item):
                    source = get_copy_source(item)
                    target_dir = abbrev(source) if source else "(copied)"
                else:
                    resolved = item.resolve()
                    if not resolved.exists():
                        broken.append(item)
                        continue
                    target_dir = abbrev(resolved.parent)
            else:
                target_dir = "(manual)"
            trial_tag = " (trial)" if _is_trial_skill(item) else ""
            groups.setdefault(target_dir, []).append(item.name + trial_tag)
        for target_dir, names in sorted(groups.items()):
            print(f"  {target_dir}:")
            for name in sorted(names):
                print(f"    {name}")
        for item in broken:
            if prune:
                remove_link(item)
                print(f"  [pruned broken link: {item.name}]")
            else:
                print(f"  [broken link: {item.name}]")

    print_grouped(global_skills, is_managed, "Global skills", global_skills_dir)
    if project_skills_dir:
        print_grouped(project_skills, is_managed, "Project skills", project_skills_dir)
    print_grouped(global_commands, lambda p: p.is_symlink(), "Global commands", global_commands_dir)
    if project_commands_dir:
        print_grouped(project_commands, lambda p: p.is_symlink(), "Project commands", project_commands_dir)

    # List registered repos
    cache_dir = get_cache_dir()
    repos = []
    if cache_dir.exists():
        for owner_dir in sorted(cache_dir.iterdir()):
            if owner_dir.is_dir():
                for repo_dir in sorted(owner_dir.iterdir()):
                    if repo_dir.is_dir():
                        repos.append(f"{owner_dir.name}/{repo_dir.name}")
    if repos:
        print(f"Repos ({abbrev(cache_dir)}):")
        for repo in repos:
            repo_path = cache_dir / repo.replace("/", os.sep)
            if is_link(repo_path):
                print(f"  {repo} -> {abbrev(repo_path.resolve())}")
            else:
                print(f"  {repo}")

    if (
        not global_skills
        and not project_skills
        and not global_commands
        and not project_commands
        and not repos
    ):
        print("No skills, commands, or repos found")



def cmd_allow(args: argparse.Namespace) -> None:
    """Apply permission presets."""
    settings_path = require_project_dir(get_project_settings_path(), "project settings")
    presets = args.presets or ["developer"]

    existing = load_settings(settings_path)
    total_perms = 0
    applied = []
    for name in presets:
        preset = get_preset(name)
        if not preset:
            print(f"Unknown preset '{name}'")
            sys.exit(1)
        existing = deep_merge(existing, preset)
        total_perms += len(preset.get("permissions", {}).get("allow", []))
        applied.append(name)
    save_settings(settings_path, existing)
    print(f"Applied {', '.join(applied)} ({total_perms} permissions) to {abbrev(settings_path)}")


def is_local_path(spec: str) -> bool:
    """Check if spec looks like a local path rather than owner/repo."""
    return spec.startswith(("/", ".", "~")) or Path(spec).expanduser().is_dir()


def add_read_permission(settings_path: Path, target_path: Path) -> None:
    """Add Read permission for a path to settings."""
    perm = f"Read({target_path}/**)"
    settings = load_settings(settings_path)
    allow_list = settings.setdefault("permissions", {}).setdefault("allow", [])
    if perm not in allow_list:
        allow_list.append(perm)
        save_settings(settings_path, settings)


def fzf_select_skills(skills: list[Path], repo_dir: Path, installed: set[str]) -> list[str]:
    """Interactive skill selection with group drill-down. Marks installed skills with *."""
    groups: dict[str, list[str]] = {}
    for skill in skills:
        group = skill.parent.name
        groups.setdefault(group, []).append(skill.name)

    def mark(name: str) -> str:
        return f"* {name}" if name in installed else f"  {name}"

    def unmark(item: str) -> str:
        return item.lstrip("* ").strip()

    def make_items(names: list[str]) -> list[str]:
        return [mark(n) for n in sorted(names)]

    if len(groups) <= 1:
        items = make_items(next(iter(groups.values()))) if groups else []
        selected = fzf_select(items, prompt="Skills> ")
        return [unmark(s) for s in selected]

    # Show default group flat, others as [group] entries
    default = "skills" if "skills" in groups else sorted(groups)[0]
    items = make_items(groups[default]) + sorted(f"[{g}]" for g in groups if g != default)
    selected = fzf_select(items, prompt="Skills> ")

    result = []
    for item in selected:
        if item.startswith("[") and item.endswith("]"):
            group_name = item[1:-1]
            sub = fzf_select(make_items(groups[group_name]), prompt=f"{group_name}> ")
            result.extend(unmark(s) for s in sub)
        else:
            result.append(unmark(item))
    return result


def fzf_select(items: list[str], prompt: str = "Select> ") -> list[str]:
    """Run fzf for multi-select; returns selected items."""
    input_text = "\n".join(items)
    result = subprocess.run(
        ["fzf", "--multi", "--prompt", prompt, "--header", "Tab to select, Enter to confirm"],
        input=input_text,
        stdout=subprocess.PIPE,
        text=True,
    )
    if result.returncode not in (0, 1):
        print("fzf not found or failed", file=sys.stderr)
        sys.exit(1)
    return [line for line in result.stdout.splitlines() if line]


def register_local_lib(repo_dir: Path) -> None:
    """Register a local directory as a symlink under repos/local/ for tracking by update."""
    local_dir = get_cache_dir() / "local"
    local_dir.mkdir(parents=True, exist_ok=True)
    link_path = local_dir / repo_dir.name
    if is_link(link_path):
        remove_link(link_path)
    elif link_path.exists():
        return  # Don't overwrite non-link
    create_dir_link(link_path, repo_dir)


def cmd_add(args: argparse.Namespace) -> None:
    """Add skills and permissions from a GitHub repo or local directory."""
    if args.local and get_git_root() is None:
        print("Not in a git repository — cannot use --local")
        sys.exit(1)
    if not args.repo:
        if not args.interactive:
            print("Provide a repo or use -i for interactive selection")
            sys.exit(1)
        cache_dir = get_cache_dir()
        repos = []
        if cache_dir.exists():
            for owner_dir in sorted(cache_dir.iterdir()):
                if owner_dir.is_dir():
                    for repo_dir in sorted(owner_dir.iterdir()):
                        if repo_dir.is_dir():
                            repos.append(f"{owner_dir.name}/{repo_dir.name}")
        if not repos:
            print("No repos cached. Run 'skillset add owner/repo' first.")
            sys.exit(1)
        selected = fzf_select(repos, prompt="Repo> ")
        if not selected:
            return
        args.repo = selected[0]

    subpath = getattr(args, "subpath", None)
    no_cache = getattr(args, "no_cache", False)
    temp_dir = None  # track temp clone for cleanup
    source_label = None  # human-readable origin for --no-cache copies

    if args.repo and "://" in args.repo:
        github_info = parse_github_url(args.repo)
        if not github_info:
            print(f"Invalid GitHub URL: {args.repo}")
            sys.exit(1)
        owner, repo_name, _branch, url_subpath = github_info
        subpath = subpath or url_subpath
        if no_cache:
            repo_dir = clone_to_temp(owner, repo_name)
            temp_dir = repo_dir.parent
            source_label = f"{owner}/{repo_name}"
        else:
            repo_dir = get_repo_dir(owner, repo_name)
            if is_link(repo_dir):
                repo_dir = repo_dir.resolve()
            else:
                repo_dir = clone_or_pull(owner, repo_name)
    elif is_local_path(args.repo):
        repo_dir = Path(args.repo).expanduser().resolve()
        if not repo_dir.is_dir():
            print(f"Directory not found: {repo_dir}")
            sys.exit(1)
        if not no_cache:
            register_local_lib(repo_dir)
    else:
        try:
            owner, repo_name = parse_repo_spec(args.repo)
        except ValueError as e:
            print(str(e))
            sys.exit(1)
        if no_cache:
            repo_dir = clone_to_temp(owner, repo_name)
            temp_dir = repo_dir.parent
            source_label = f"{owner}/{repo_name}"
        else:
            repo_dir = get_repo_dir(owner, repo_name)
            if is_link(repo_dir):
                repo_dir = repo_dir.resolve()
            else:
                repo_dir = clone_or_pull(owner, repo_name)

    source_dir = repo_dir / subpath if subpath else repo_dir
    if subpath and not source_dir.is_dir():
        print(f"Path not found in repo: {subpath}")
        sys.exit(1)

    # Link skills (global or project)
    use_copy = getattr(args, "copy", False) or no_cache
    skills_dir = get_project_skills_dir() if args.local else get_global_skills_dir()
    skill_filter = set(args.skills) if getattr(args, "skills", None) else None
    if args.interactive:
        available_skills = find_skills(source_dir)
        if available_skills:
            installed = {p.name for p in skills_dir.iterdir() if is_managed(p)} if skills_dir.exists() else set()
            selected = fzf_select_skills(available_skills, source_dir, installed)
            linked_skills = link_skills(source_dir, skills_dir, only=set(selected), copy=use_copy, source_label=source_label)
        else:
            linked_skills = []
    else:
        linked_skills = link_skills(source_dir, skills_dir, only=skill_filter, copy=use_copy, source_label=source_label)

    if linked_skills:
        verb = "Copied" if use_copy else "Linked"
        print(f"{verb} {len(linked_skills)} skill(s) to {abbrev(skills_dir)}:")
        for skill_name in sorted(linked_skills):
            print(f"  - {skill_name}")

    # Link commands (global or project)
    commands_dir = get_project_commands_dir() if args.local else get_global_commands_dir()
    if args.interactive:
        available_commands = find_commands(source_dir)
        if available_commands:
            selected = fzf_select(sorted(c.name for c in available_commands), prompt="Commands> ")
            linked_commands = link_commands(source_dir, commands_dir, only=set(selected), copy=use_copy)
        else:
            linked_commands = []
    else:
        linked_commands = link_commands(source_dir, commands_dir, copy=use_copy)

    if linked_commands:
        verb = "Copied" if use_copy else "Linked"
        print(f"{verb} {len(linked_commands)} command(s) to {abbrev(commands_dir)}:")
        for cmd_name in sorted(linked_commands):
            print(f"  - {cmd_name}")

    # Add read permission for source directory if we linked anything
    if linked_skills or linked_commands:
        settings_path = get_project_settings_path() if args.local else get_global_settings_path()
        add_read_permission(settings_path, repo_dir)
        print(f"Added Read permission for {abbrev(repo_dir)}")

    # Merge permissions (project if in a git repo)
    settings_path = get_project_settings_path()
    if settings_path:
        merged_keys = merge_permissions(repo_dir, settings_path)
    else:
        merged_keys = []

    if merged_keys:
        print(f"Merged permissions into {abbrev(settings_path)}:")
        for key in sorted(merged_keys):
            print(f"  - {key}")

    # Record install options for update
    if linked_skills or linked_commands:
        # Derive a repo key from the repo_dir relative to cache, or use abs path for local
        try:
            rel = repo_dir.relative_to(get_cache_dir())
            repo_key = str(rel)
        except ValueError:
            repo_key = str(repo_dir)
        is_trial = getattr(args, "trial", False)
        # --try sets trial; no --try with -s preserves existing; no --try without -s clears trial
        if is_trial:
            trial_value = True
        elif getattr(args, "skills", None):
            trial_value = None  # adding specific skills — don't change trial status
        else:
            trial_value = False  # full re-add — promote to permanent
        record_install(
            repo_key,
            subpath=subpath,
            copy=use_copy,
            scope="local" if args.local else "global",
            trial=trial_value,
            skills=list(linked_skills),
            commands=list(linked_commands),
        )

    if not linked_skills and not linked_commands and not merged_keys:
        print("No skills or permissions found in repo")

    # Clean up temp clone
    if temp_dir:
        shutil.rmtree(temp_dir, ignore_errors=True)


def cmd_remove(args: argparse.Namespace) -> None:
    """Remove a skill by name, or interactively select skills to remove."""
    if args.local and get_git_root() is None:
        print("Not in a git repository — cannot use --local")
        sys.exit(1)
    skills_dir = require_project_dir(get_project_skills_dir()) if args.local else get_global_skills_dir()

    if args.interactive:
        installed = sorted(p.name for p in skills_dir.iterdir() if is_managed(p)) if skills_dir.exists() else []
        if not installed:
            print(f"No managed skills in {abbrev(skills_dir)}")
            return
        scope = "project" if args.local else "global"
        selected = fzf_select(installed, prompt=f"Remove {scope} skills> ")
        for name in selected:
            remove_managed(skills_dir / name)
            print(f"Removed {name} from {abbrev(skills_dir)}")
        return

    if not args.name:
        print("Provide a skill name or use -i for interactive selection")
        sys.exit(1)

    # Repo spec (owner/repo) — remove everything installed from that repo.
    if "/" in args.name and not any(c in args.name for c in "*?["):
        repo_key = args.name
        opts = get_install_options(repo_key)
        if opts is None:
            print(f"No repo '{repo_key}' recorded in manifest")
            sys.exit(1)
        scope = opts.get("scope", "global")
        skills_target = get_global_skills_dir() if scope == "global" else require_project_dir(get_project_skills_dir())
        commands_target = get_global_commands_dir() if scope == "global" else require_project_dir(get_project_commands_dir())

        removed = 0
        for name in opts.get("skills", []):
            p = skills_target / name
            if p.exists() and is_managed(p):
                remove_managed(p)
                print(f"Removed skill {name} from {abbrev(skills_target)}")
                removed += 1
        for name in opts.get("commands", []):
            p = commands_target / name
            if p.exists() and (p.is_symlink() or p.is_file()):
                p.unlink()
                print(f"Removed command {name} from {abbrev(commands_target)}")
                removed += 1

        # Drop manifest entry
        manifest = load_manifest()
        manifest.pop(repo_key, None)
        save_manifest(manifest)

        if removed == 0:
            print(f"No managed items from {repo_key} to remove")
        return

    # Glob pattern support (e.g. "bs-*")
    if any(c in args.name for c in "*?["):
        if not skills_dir.exists():
            print(f"No skills in {abbrev(skills_dir)}")
            sys.exit(1)
        matched = sorted(
            p.name for p in skills_dir.iterdir()
            if fnmatch.fnmatch(p.name, args.name) and is_managed(p)
        )
        if not matched:
            print(f"No managed skills matching '{args.name}' in {abbrev(skills_dir)}")
            sys.exit(1)
        for name in matched:
            remove_managed(skills_dir / name)
            print(f"Removed {name} from {abbrev(skills_dir)}")
        return

    skill_path = skills_dir / args.name

    if not skill_path.exists():
        print(f"Skill '{args.name}' not found in {abbrev(skills_dir)}")
        sys.exit(1)

    if is_managed(skill_path):
        remove_managed(skill_path)
        print(f"Removed {args.name} from {abbrev(skills_dir)}")
    else:
        print(f"'{args.name}' is not managed by skillset - remove manually if intended")
        sys.exit(1)


def _resolve_update_options(repo_key: str, args: argparse.Namespace) -> tuple[str | None, bool, str]:
    """Resolve subpath/copy/scope from manifest, with CLI flags as overrides."""
    opts = get_install_options(repo_key) or {}
    use_copy = getattr(args, "copy", False) or opts.get("copy", False)
    subpath = opts.get("subpath")
    scope = opts.get("scope", "global")
    # CLI --global flag overrides saved scope
    if getattr(args, "g", False):
        scope = "global"
    return subpath, use_copy, scope


def _items_pointing_at(target_dir: Path, source_dir: Path, is_file: bool = False) -> list[str]:
    """Return names in target_dir that are managed entries resolving into source_dir.

    Used to seed the manifest's per-repo skill/command list for installs that
    predate per-repo tracking.
    """
    if not target_dir.exists():
        return []
    try:
        src_resolved = source_dir.resolve()
    except OSError:
        return []
    out: list[str] = []
    for p in target_dir.iterdir():
        if is_file and not (p.is_file() or p.is_symlink()):
            continue
        if not is_file and not (p.is_dir() or p.is_symlink()):
            continue
        if is_link(p):
            try:
                resolved = p.resolve()
            except OSError:
                continue
            # For files, check parent; for dirs, check the path itself
            check = resolved.parent if is_file else resolved
            try:
                check.relative_to(src_resolved)
            except ValueError:
                continue
            out.append(p.name)
        elif not is_file and is_managed_copy(p):
            src = get_copy_source(p) or ""
            if src and str(src_resolved) in src:
                out.append(p.name)
    return out


def _update_one_repo(
    repo_key: str,
    source_dir: Path,
    args: argparse.Namespace,
) -> tuple[int, int]:
    """Refresh skills/commands for one repo. Returns (skills, commands) counts."""
    subpath, use_copy, scope = _resolve_update_options(repo_key, args)
    opts = get_install_options(repo_key) or {}

    skills_dir = get_global_skills_dir() if scope == "global" else require_project_dir(get_project_skills_dir())
    commands_dir = get_global_commands_dir() if scope == "global" else require_project_dir(get_project_commands_dir())

    want_new = getattr(args, "new", False)
    cli_skills = set(args.skills) if getattr(args, "skills", None) else None

    # Resolve skill filter
    recorded_skills = opts.get("skills")
    if recorded_skills is None and not want_new:
        # Legacy manifest — seed from target dir by resolving managed entries
        recorded_skills = _items_pointing_at(skills_dir, source_dir)
        if recorded_skills:
            print(f"  Seeded skill list for {repo_key}: {', '.join(sorted(recorded_skills))}")

    if want_new:
        skill_filter = cli_skills  # None means all
    elif cli_skills is not None:
        skill_filter = cli_skills
    else:
        skill_filter = set(recorded_skills or [])

    # Commands: same treatment but no CLI filter currently
    recorded_commands = opts.get("commands")
    if recorded_commands is None and not want_new:
        recorded_commands = _items_pointing_at(commands_dir, source_dir, is_file=True)

    if want_new:
        command_filter = None
    else:
        command_filter = set(recorded_commands or [])

    # Empty filter (not None) means "nothing to refresh" — avoid linking all.
    if skill_filter is not None and not skill_filter:
        linked_skills: list[str] = []
    else:
        linked_skills = link_skills(source_dir, skills_dir, only=skill_filter, copy=use_copy)

    if command_filter is not None and not command_filter:
        linked_commands: list[str] = []
    else:
        linked_commands = link_commands(source_dir, commands_dir, only=command_filter, copy=use_copy)

    # Refresh manifest with the items we just linked so the list stays accurate.
    record_install(
        repo_key,
        subpath=subpath,
        copy=use_copy,
        scope=scope,
        skills=linked_skills,
        commands=linked_commands,
        replace_items=want_new,
    )

    return len(linked_skills), len(linked_commands)


def cmd_update(args: argparse.Namespace) -> None:
    """Update repo(s) and refresh links (or copies) and permissions."""
    cache_dir = get_cache_dir()

    if args.repo:
        try:
            owner, repo_name = parse_repo_spec(args.repo)
        except ValueError as e:
            print(str(e))
            sys.exit(1)

        repo_dir = get_repo_dir(owner, repo_name)
        if not repo_dir.exists():
            print(f"Repo {args.repo} not installed. Use 'skillset add {args.repo}' first.")
            sys.exit(1)

        if not is_link(repo_dir):
            clone_or_pull(owner, repo_name)

        repo_key = f"{owner}/{repo_name}"
        subpath, _use_copy, scope = _resolve_update_options(repo_key, args)
        if scope == "local" and get_git_root() is None:
            print(f"Repo {repo_key} was installed with --local but you are not in a git repo")
            sys.exit(1)
        resolved_dir = repo_dir.resolve() if is_link(repo_dir) else repo_dir
        source_dir = resolved_dir / subpath if subpath else resolved_dir

        s, c = _update_one_repo(repo_key, source_dir, args)
        print(f"Updated {s} skill(s), {c} command(s)")
    else:
        total_skills = 0
        total_commands = 0

        if cache_dir.exists():
            for owner_dir in cache_dir.iterdir():
                if not owner_dir.is_dir():
                    continue
                for repo_dir in owner_dir.iterdir():
                    if not repo_dir.is_dir():
                        continue
                    if not is_link(repo_dir):
                        clone_or_pull(owner_dir.name, repo_dir.name)
                    resolved_dir = repo_dir.resolve() if is_link(repo_dir) else repo_dir
                    repo_key = f"{owner_dir.name}/{repo_dir.name}"
                    subpath, _use_copy, scope = _resolve_update_options(repo_key, args)
                    source_dir = resolved_dir / subpath if subpath else resolved_dir

                    if scope == "local" and get_git_root() is None:
                        print(f"  Skipping {repo_key} (local scope, not in a git repo)")
                        continue
                    s, c = _update_one_repo(repo_key, source_dir, args)
                    total_skills += s
                    total_commands += c

        if total_skills == 0 and total_commands == 0:
            print("No repos installed")
        else:
            print(f"Updated ({total_skills} skill(s), {total_commands} command(s))")


def cmd_apply(args: argparse.Namespace) -> None:
    """Apply skills.toml — install all declared skills."""
    import tomllib

    file_path = Path(getattr(args, "file", None) or "skillset.toml")
    if not file_path.exists():
        print(f"No skillset.toml found at {file_path}")
        sys.exit(1)

    with open(file_path, "rb") as f:
        config = tomllib.load(f)

    skills_config = config.get("skills")
    if skills_config is None:
        print("No [skills] section found in skillset.toml")
        sys.exit(1)

    links_config = config.get("links", {})
    for local_path, target in links_config.items():
        link = Path(local_path)
        if link.is_symlink():
            print(f"Link already exists: {local_path} -> {os.readlink(local_path)}")
        elif link.exists():
            print(f"Skipping {local_path}: exists and is not a symlink")
        else:
            link.parent.mkdir(parents=True, exist_ok=True)
            link.symlink_to(target)
            print(f"Linked {local_path} -> {target}")
        ignored = subprocess.run(
            ["git", "check-ignore", "-q", local_path],
            capture_output=True,
        ).returncode == 0
        if not ignored:
            print(f"  Warning: {local_path} is not in .gitignore")

    for repo, value in skills_config.items():
        if isinstance(value, bool):
            if not value:
                continue  # false = disabled
            entry_skills, entry_local, entry_copy, entry_subpath = None, False, False, None
        elif isinstance(value, list):
            entry_skills, entry_local, entry_copy, entry_subpath = value, False, False, None
        elif isinstance(value, dict):
            entry_skills = value.get("skills")
            entry_local = value.get("local", False)
            entry_copy = value.get("copy", False)
            entry_subpath = value.get("path")
        else:
            print(f"Invalid entry for {repo!r}")
            sys.exit(1)

        print(f"\nAdding {repo}...")
        cmd_add(argparse.Namespace(
            repo=repo,
            local=entry_local,
            skills=entry_skills,
            subpath=entry_subpath,
            copy=entry_copy,
            no_cache=False,
            trial=False,
            interactive=False,
        ))


def cmd_clean(args: argparse.Namespace) -> None:
    """Remove all trial skills."""
    manifest = load_manifest()
    trial_repos = {k: v for k, v in manifest.items() if v.get("trial")}

    if not trial_repos:
        print("No trial skills to clean")
        return

    removed = 0
    for repo_key, opts in trial_repos.items():
        scope = opts.get("scope", "global")
        if scope == "local":
            skills_dir = get_project_skills_dir()
            if skills_dir is None:
                print(f"  Skipping {repo_key} (local scope, not in a git repo)")
                continue
        else:
            skills_dir = get_global_skills_dir()

        if skills_dir.exists():
            for item in sorted(skills_dir.iterdir()):
                if not is_managed(item):
                    continue
                # Check if this skill points back to the trial repo
                if is_managed_copy(item):
                    source = get_copy_source(item) or ""
                elif is_link(item):
                    source = str(item.resolve())
                else:
                    continue
                if repo_key in source or abbrev(repo_key) in abbrev(source):
                    remove_managed(item)
                    print(f"  Removed {item.name}")
                    removed += 1

        # Remove from manifest
        del manifest[repo_key]

        # Remove cached repo if no other manifest entries reference it
        remaining_keys = set(manifest.keys())
        # repo_key is like "owner/repo" or an absolute path
        repo_dir = get_cache_dir() / repo_key.replace("/", os.sep)
        if repo_dir.exists() and not any(k.startswith(repo_key) for k in remaining_keys):
            if is_link(repo_dir):
                remove_link(repo_dir)
            else:
                shutil.rmtree(repo_dir)
            # Clean up empty parent dirs
            parent = repo_dir.parent
            if parent.exists() and not any(parent.iterdir()):
                parent.rmdir()
            print(f"  Removed cached repo {repo_key}")

    save_manifest(manifest)
    print(f"Cleaned {removed} trial skill(s) from {len(trial_repos)} repo(s)")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="skillset",
        description="Manage AI skills and permissions across projects",
    )
    from skillset import __version__
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # list
    p_list = subparsers.add_parser("list", help="list installed skills")
    p_list.add_argument(
        "--prune", action="store_true", help="remove broken links"
    )

    # allow
    p_apply = subparsers.add_parser("allow", help="allow permission presets")
    p_apply.add_argument(
        "presets", nargs="*", help="preset name(s) to allow (default: developer)"
    )

    # add
    p_add = subparsers.add_parser("add", help="add skills from a GitHub repo")
    p_add.add_argument("repo", nargs="?", help="repo in owner/repo format")
    p_add.add_argument(
        "-l", "--local", dest="local", action="store_true", help="install skills in project scope"
    )
    p_add.add_argument(
        "-i", "--interactive", action="store_true", help="select skills interactively with fzf"
    )
    p_add.add_argument(
        "-s", "--skill", dest="skills", metavar="SKILL", action="append",
        help="add only this skill by name (can be repeated)"
    )
    p_add.add_argument(
        "-p", "--path", dest="subpath", metavar="PATH",
        help="subdirectory within the repo to use as root"
    )
    p_add.add_argument(
        "--copy", action="store_true",
        help="copy files instead of symlinking (for Windows without admin)"
    )
    p_add.add_argument(
        "--no-cache", dest="no_cache", action="store_true",
        help="clone to a temp dir, copy skills, then clean up (no persistent repo cache)"
    )
    p_add.add_argument(
        "--try", dest="trial", action="store_true",
        help="install skills on a trial basis (remove later with 'skillset clean')"
    )

    # apply
    p_apply_cmd = subparsers.add_parser("apply", help="install skills declared in skills.toml")
    p_apply_cmd.add_argument(
        "--file", metavar="PATH", help="path to skillset.toml (default: ./skillset.toml)"
    )

    # update
    p_update = subparsers.add_parser("update", help="update repo(s) and refresh links")
    p_update.add_argument("repo", nargs="?", help="specific repo to update (optional)")
    p_update.add_argument(
        "-g", "--global", dest="g", action="store_true", help="update global skills"
    )
    p_update.add_argument(
        "--copy", action="store_true",
        help="copy files instead of symlinking (for Windows without admin)"
    )
    p_update.add_argument(
        "--new", action="store_true",
        help="also link new skills/commands not currently linked"
    )
    p_update.add_argument(
        "-s", "--skill", dest="skills", metavar="SKILL", action="append",
        help="only update the named skill (repeatable)"
    )

    # clean
    subparsers.add_parser("clean", help="remove all trial skills")

    # remove
    p_remove = subparsers.add_parser("remove", help="remove a skill by name")
    p_remove.add_argument("name", nargs="?", help="skill name, glob (e.g. bs-*), or owner/repo")
    p_remove.add_argument(
        "-l", "--local", dest="local", action="store_true", help="remove from project skills"
    )
    p_remove.add_argument(
        "-i", "--interactive", action="store_true", help="select skills to remove with fzf"
    )

    args = parser.parse_args()

    handlers = {
        "list": cmd_list,
        "allow": cmd_allow,
        "add": cmd_add,
        "apply": cmd_apply,
        "update": cmd_update,
        "clean": cmd_clean,
        "remove": cmd_remove,
    }
    handlers[args.command](args)


if __name__ == "__main__":
    main()
