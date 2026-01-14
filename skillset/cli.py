"""CLI for managing AI skills and permissions across projects."""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from skillset.builtins import PRESETS as BUILTIN_PRESETS

IS_WINDOWS = sys.platform == "win32"
CLAUDE_SETTINGS_FILE = ".claude/settings.json"


def get_presets_dir() -> Path:
    """Get the directory where permission presets are stored."""
    return Path.home() / ".config" / "skillset" / "presets"


def get_cache_dir() -> Path:
    """Get the directory where repos are cached."""
    return Path.home() / ".cache" / "skillset" / "repos"


def get_global_skills_dir() -> Path:
    """Get global Claude skills directory."""
    return Path.home() / ".claude" / "skills"


def get_project_skills_dir() -> Path:
    """Get project-local Claude skills directory."""
    return Path.cwd() / ".claude" / "skills"


def get_global_settings_path() -> Path:
    """Get global Claude settings.local path (user preferences)."""
    return Path.home() / ".claude" / "settings.local.json"


def get_project_settings_path() -> Path:
    """Get project-local Claude settings.local path (user preferences)."""
    return Path.cwd() / ".claude" / "settings.local.json"


def parse_repo_spec(spec: str) -> tuple[str, str]:
    """Parse 'owner/repo' into (owner, repo)."""
    parts = spec.strip().split("/")
    if len(parts) != 2:
        raise ValueError(f"Invalid repo format: {spec}. Use 'owner/repo'")
    return parts[0], parts[1]


def get_repo_dir(owner: str, repo: str) -> Path:
    """Get the cache directory for a repo."""
    return get_cache_dir() / owner / repo


def clone_or_pull(owner: str, repo: str) -> Path:
    """Clone repo if not exists, or pull if it does. Returns repo path."""
    repo_dir = get_repo_dir(owner, repo)
    https_url = f"https://github.com/{owner}/{repo}.git"
    ssh_url = f"git@github.com:{owner}/{repo}.git"

    if repo_dir.exists():
        print(f"Updating {owner}/{repo}...")
        subprocess.run(["git", "pull"], cwd=repo_dir, check=True, capture_output=True)
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
        # Junctions appear as directories but have reparse points
        return path.is_symlink() or (path.is_dir() and os.path.islink(str(path)))
    return path.is_symlink()


def remove_link(path: Path) -> None:
    """Remove a symlink or junction."""
    if IS_WINDOWS and path.is_dir():
        # Junctions need rmdir, not unlink
        os.rmdir(path)
    else:
        path.unlink()


def link_skills(repo_dir: Path, target_dir: Path) -> list[str]:
    """Link skill directories from repo to target skills dir."""
    target_dir.mkdir(parents=True, exist_ok=True)
    linked = []
    for skill_dir in find_skills(repo_dir):
        skill_name = skill_dir.name
        link_path = target_dir / skill_name
        if is_link(link_path):
            remove_link(link_path)
        elif link_path.exists():
            print(f"  Skipping {skill_name}: already exists (not a link)")
            continue
        create_dir_link(link_path, skill_dir)
        linked.append(skill_name)
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


def detect_project_types(project_dir: Path) -> list[str]:
    """Detect which built-in presets apply to a project."""
    detected = []
    if (project_dir / ".git").exists():
        detected.append("git")
    if (project_dir / "package.json").exists():
        detected.append("node")
    if any(
        (project_dir / f).exists()
        for f in ("pyproject.toml", "setup.py", "requirements.txt", "Pipfile")
    ):
        detected.append("python")
    if any(
        (project_dir / f).exists()
        for f in ("Dockerfile", "docker-compose.yml", "docker-compose.yaml", "compose.yml")
    ):
        detected.append("docker")
    if any((project_dir / f).exists() for f in ("k8s", "kubernetes", "helm", "Chart.yaml")):
        detected.append("k8s")
    return detected


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


def load_user_preset(name: str) -> dict | None:
    """Load a user-saved preset by name."""
    preset_path = get_presets_dir() / f"{name}.json"
    if preset_path.exists():
        return json.loads(preset_path.read_text())
    return None


def save_user_preset(name: str, settings: dict) -> Path:
    """Save settings as a user preset."""
    presets_dir = get_presets_dir()
    presets_dir.mkdir(parents=True, exist_ok=True)
    preset_path = presets_dir / f"{name}.json"
    preset_path.write_text(json.dumps(settings, indent=2) + "\n")
    return preset_path


def get_preset(name: str) -> dict | None:
    """Get a preset by name (checks user presets first, then builtins)."""
    user_preset = load_user_preset(name)
    if user_preset:
        return user_preset
    return BUILTIN_PRESETS.get(name)


# Command handlers


def cmd_list(args: argparse.Namespace) -> None:
    """List installed skills and saved presets."""
    global_dir = get_global_skills_dir()
    project_dir = get_project_skills_dir()
    presets_dir = get_presets_dir()

    global_skills = sorted(global_dir.iterdir()) if global_dir.exists() else []
    project_skills = sorted(project_dir.iterdir()) if project_dir.exists() else []
    saved_presets = sorted(presets_dir.glob("*.json")) if presets_dir.exists() else []

    if global_skills:
        print(f"Global skills ({global_dir}):")
        for skill in global_skills:
            suffix = " -> " + str(skill.resolve()) if is_link(skill) else ""
            print(f"  {skill.name}{suffix}")

    if project_skills:
        print(f"Project skills ({project_dir}):")
        for skill in project_skills:
            suffix = " -> " + str(skill.resolve()) if is_link(skill) else ""
            print(f"  {skill.name}{suffix}")

    if saved_presets:
        print(f"Saved presets ({presets_dir}):")
        for preset in saved_presets:
            print(f"  {preset.stem}")

    if not global_skills and not project_skills and not saved_presets:
        print("No skills or presets found")


def cmd_save(args: argparse.Namespace) -> None:
    """Save current project permissions as a reusable preset."""
    settings_path = get_project_settings_path()
    if not settings_path.exists():
        print(f"No settings found at {settings_path}")
        sys.exit(1)

    settings = load_settings(settings_path)
    preset_path = save_user_preset(args.name, settings)
    print(f"Saved preset '{args.name}' to {preset_path}")


def cmd_apply(args: argparse.Namespace) -> None:
    """Apply permission presets (auto-detect or specific)."""
    settings_path = get_project_settings_path()

    # Specific preset(s) given
    if args.presets:
        existing = load_settings(settings_path)
        total_perms = 0
        applied = []
        for name in args.presets:
            preset = get_preset(name)
            if not preset:
                print(f"Unknown preset '{name}'")
                sys.exit(1)
            existing = deep_merge(existing, preset)
            total_perms += len(preset.get("permissions", {}).get("allow", []))
            applied.append(name)
        save_settings(settings_path, existing)
        print(f"Applied {', '.join(applied)} ({total_perms} permissions) to {settings_path}")
        return

    # Auto-detect
    project_dir = Path.cwd()
    detected = detect_project_types(project_dir)

    if not detected:
        print("No project types detected. Use 'skillset apply <preset> -p' to apply manually.")
        return

    print(f"Detected: {', '.join(detected)}")

    if args.dry_run:
        print("Would apply these presets (dry-run):")
        for name in detected:
            if name in BUILTIN_PRESETS:
                perms = BUILTIN_PRESETS[name].get("permissions", {}).get("allow", [])
                print(f"  {name}: {len(perms)} permission(s)")
        return

    existing = load_settings(settings_path)
    total_perms = 0
    for name in detected:
        if name in BUILTIN_PRESETS:
            preset = BUILTIN_PRESETS[name]
            existing = deep_merge(existing, preset)
            total_perms += len(preset.get("permissions", {}).get("allow", []))

    save_settings(settings_path, existing)
    print(f"Applied {len(detected)} preset(s) ({total_perms} permissions) to {settings_path}")


def is_local_path(spec: str) -> bool:
    """Check if spec looks like a local path rather than owner/repo."""
    return spec.startswith(("/", ".", "~"))


def cmd_add(args: argparse.Namespace) -> None:
    """Add skills and permissions from a GitHub repo or local directory."""
    if is_local_path(args.repo):
        repo_dir = Path(args.repo).expanduser().resolve()
        if not repo_dir.is_dir():
            print(f"Directory not found: {repo_dir}")
            sys.exit(1)
    else:
        try:
            owner, repo_name = parse_repo_spec(args.repo)
        except ValueError as e:
            print(str(e))
            sys.exit(1)
        repo_dir = clone_or_pull(owner, repo_name)

    # Link skills (global or project)
    skills_dir = get_global_skills_dir() if args.g else get_project_skills_dir()
    linked = link_skills(repo_dir, skills_dir)

    if linked:
        print(f"Linked {len(linked)} skill(s) to {skills_dir}:")
        for skill_name in sorted(linked):
            print(f"  - {skill_name}")

    # Merge permissions (always project)
    settings_path = get_project_settings_path()
    merged_keys = merge_permissions(repo_dir, settings_path)

    if merged_keys:
        print(f"Merged permissions into {settings_path}:")
        for key in sorted(merged_keys):
            print(f"  - {key}")

    if not linked and not merged_keys:
        print("No skills or permissions found in repo")


def cmd_remove(args: argparse.Namespace) -> None:
    """Remove a skill by name."""
    skills_dir = get_global_skills_dir() if args.g else get_project_skills_dir()
    skill_path = skills_dir / args.name

    if not skill_path.exists():
        print(f"Skill '{args.name}' not found in {skills_dir}")
        sys.exit(1)

    if is_link(skill_path):
        remove_link(skill_path)
        print(f"Removed {args.name} from {skills_dir}")
    else:
        print(f"'{args.name}' is not a symlink - remove manually if intended")
        sys.exit(1)


def cmd_update(args: argparse.Namespace) -> None:
    """Update repo(s) and refresh symlinks and permissions."""
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

        clone_or_pull(owner, repo_name)

        # Refresh skills (global or project)
        skills_dir = get_global_skills_dir() if args.g else get_project_skills_dir()
        linked = link_skills(repo_dir, skills_dir)
        print(f"Updated {len(linked)} skill(s)")

        # Refresh permissions (always project)
        settings_path = get_project_settings_path()
        merged_keys = merge_permissions(repo_dir, settings_path)
        if merged_keys:
            print(f"Refreshed {len(merged_keys)} permission key(s)")
    else:
        if not cache_dir.exists():
            print("No repos installed")
            return

        skills_dir = get_global_skills_dir() if args.g else get_project_skills_dir()
        settings_path = get_project_settings_path()
        total_skills = 0
        total_perms = 0

        for owner_dir in cache_dir.iterdir():
            if not owner_dir.is_dir():
                continue
            for repo_dir in owner_dir.iterdir():
                if not repo_dir.is_dir():
                    continue
                clone_or_pull(owner_dir.name, repo_dir.name)
                linked = link_skills(repo_dir, skills_dir)
                total_skills += len(linked)
                merged_keys = merge_permissions(repo_dir, settings_path)
                total_perms += len(merged_keys)

        print(f"All repos updated ({total_skills} skill(s), {total_perms} permission key(s))")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="skillset",
        description="Manage AI skills and permissions across projects",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # list
    subparsers.add_parser("list", help="list installed skills")

    # save
    p_save = subparsers.add_parser("save", help="save project permissions as reusable preset")
    p_save.add_argument("name", help="preset name")

    # apply
    p_apply = subparsers.add_parser(
        "apply", help="apply permission presets (auto-detect or specific)"
    )
    p_apply.add_argument(
        "presets", nargs="*", help="preset name(s) to apply (auto-detect if omitted)"
    )
    p_apply.add_argument("--dry-run", action="store_true", help="show what would be applied")

    # add
    p_add = subparsers.add_parser("add", help="add skills from a GitHub repo")
    p_add.add_argument("repo", help="repo in owner/repo format")
    p_add.add_argument(
        "-g", "--global", dest="g", action="store_true", help="install skills globally"
    )

    # update
    p_update = subparsers.add_parser("update", help="update repo(s) and refresh links")
    p_update.add_argument("repo", nargs="?", help="specific repo to update (optional)")
    p_update.add_argument(
        "-g", "--global", dest="g", action="store_true", help="update global skills"
    )

    # remove
    p_remove = subparsers.add_parser("remove", help="remove a skill by name")
    p_remove.add_argument("name", help="skill name to remove")
    p_remove.add_argument(
        "-g", "--global", dest="g", action="store_true", help="remove from global skills"
    )

    args = parser.parse_args()

    handlers = {
        "list": cmd_list,
        "save": cmd_save,
        "apply": cmd_apply,
        "add": cmd_add,
        "update": cmd_update,
        "remove": cmd_remove,
    }
    handlers[args.command](args)


if __name__ == "__main__":
    main()
