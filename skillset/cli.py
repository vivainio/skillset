"""CLI for managing AI skills and permissions across projects."""

import argparse
import json
import subprocess
import sys
from pathlib import Path

from skillset.builtins import PRESETS as BUILTIN_PRESETS

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
    repo_url = f"https://github.com/{owner}/{repo}.git"

    if repo_dir.exists():
        print(f"Updating {owner}/{repo}...")
        subprocess.run(["git", "pull"], cwd=repo_dir, check=True, capture_output=True)
    else:
        print(f"Cloning {owner}/{repo}...")
        repo_dir.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "clone", repo_url, str(repo_dir)], check=True, capture_output=True)

    return repo_dir


def find_skills(repo_dir: Path) -> list[Path]:
    """Find skill directories in a repo. A skill is a dir with a markdown file."""
    skills = []
    for md_file in repo_dir.glob("**/*.md"):
        if any(part.startswith(".") for part in md_file.relative_to(repo_dir).parts):
            continue
        if md_file.parent == repo_dir and md_file.name.lower() == "readme.md":
            continue
        skill_dir = md_file.parent
        if skill_dir not in skills and skill_dir != repo_dir:
            skills.append(skill_dir)
    return skills


def link_skills(repo_dir: Path, target_dir: Path) -> list[str]:
    """Symlink skill directories from repo to target skills dir."""
    target_dir.mkdir(parents=True, exist_ok=True)
    linked = []
    for skill_dir in find_skills(repo_dir):
        skill_name = skill_dir.name
        link_path = target_dir / skill_name
        if link_path.is_symlink():
            link_path.unlink()
        elif link_path.exists():
            print(f"  Skipping {skill_name}: already exists (not a symlink)")
            continue
        link_path.symlink_to(skill_dir)
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


# Command handlers


def cmd_builtins(args: argparse.Namespace) -> None:
    """List available built-in permission presets."""
    print("Built-in presets:")
    for name, preset in BUILTIN_PRESETS.items():
        perms = preset.get("permissions", {}).get("allow", [])
        print(f"  {name}: {len(perms)} permission(s)")


def cmd_use(args: argparse.Namespace) -> None:
    """Apply a built-in permission preset."""
    if args.name not in BUILTIN_PRESETS:
        print(f"Unknown preset '{args.name}'. Use 'skillset builtins' to see available presets.")
        sys.exit(1)

    preset = BUILTIN_PRESETS[args.name]
    settings_path = get_global_settings_path() if args.g else get_project_settings_path()

    existing = load_settings(settings_path)
    merged = deep_merge(existing, preset)
    save_settings(settings_path, merged)

    perms = preset.get("permissions", {}).get("allow", [])
    print(f"Applied '{args.name}' preset ({len(perms)} permissions) to {settings_path}")


def cmd_apply(args: argparse.Namespace) -> None:
    """Auto-detect project type and apply appropriate presets."""
    project_dir = Path.cwd()
    detected = detect_project_types(project_dir)

    if not detected:
        print("No project types detected. Use 'skillset use <preset>' to apply manually.")
        return

    print(f"Detected: {', '.join(detected)}")

    if args.dry_run:
        print("Would apply these presets (dry-run):")
        for name in detected:
            if name in BUILTIN_PRESETS:
                perms = BUILTIN_PRESETS[name].get("permissions", {}).get("allow", [])
                print(f"  {name}: {len(perms)} permission(s)")
        return

    settings_path = get_global_settings_path() if args.g else get_project_settings_path()
    existing = load_settings(settings_path)

    total_perms = 0
    for name in detected:
        if name in BUILTIN_PRESETS:
            preset = BUILTIN_PRESETS[name]
            existing = deep_merge(existing, preset)
            total_perms += len(preset.get("permissions", {}).get("allow", []))

    save_settings(settings_path, existing)
    print(f"Applied {len(detected)} preset(s) ({total_perms} permissions) to {settings_path}")


def cmd_add(args: argparse.Namespace) -> None:
    """Add skills and permissions from a GitHub repo."""
    try:
        owner, repo_name = parse_repo_spec(args.repo)
    except ValueError as e:
        print(str(e))
        sys.exit(1)

    repo_dir = clone_or_pull(owner, repo_name)

    # Link skills
    skills_dir = get_global_skills_dir() if args.g else get_project_skills_dir()
    linked = link_skills(repo_dir, skills_dir)

    if linked:
        print(f"Linked {len(linked)} skill(s) to {skills_dir}:")
        for skill_name in sorted(linked):
            print(f"  - {skill_name}")

    # Merge permissions
    settings_path = get_global_settings_path() if args.g else get_project_settings_path()
    merged_keys = merge_permissions(repo_dir, settings_path)

    if merged_keys:
        print(f"Merged permissions into {settings_path}:")
        for key in sorted(merged_keys):
            print(f"  - {key}")

    if not linked and not merged_keys:
        print("No skills or permissions found in repo")


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
        skills_dir = get_global_skills_dir() if args.g else get_project_skills_dir()
        linked = link_skills(repo_dir, skills_dir)
        print(f"Updated {len(linked)} skill(s)")

        settings_path = get_global_settings_path() if args.g else get_project_settings_path()
        merged_keys = merge_permissions(repo_dir, settings_path)
        if merged_keys:
            print(f"Refreshed {len(merged_keys)} permission key(s)")
    else:
        if not cache_dir.exists():
            print("No repos installed")
            return

        for owner_dir in cache_dir.iterdir():
            if not owner_dir.is_dir():
                continue
            for repo_dir in owner_dir.iterdir():
                if not repo_dir.is_dir():
                    continue
                clone_or_pull(owner_dir.name, repo_dir.name)
        print("All repos updated (use -g or -p to refresh links)")


def add_target_args(parser: argparse.ArgumentParser) -> None:
    """Add mutually exclusive -g/--global and -p/--project arguments."""
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "-g", "--global", dest="g", action="store_true", help="target global settings"
    )
    group.add_argument(
        "-p", "--project", dest="p", action="store_true", help="target project settings"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="skillset",
        description="Manage AI skills and permissions across projects",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # builtins
    subparsers.add_parser("builtins", help="list built-in permission presets")

    # use
    p_use = subparsers.add_parser("use", help="apply a built-in permission preset")
    p_use.add_argument("name", help="preset name (e.g., developer, python, node)")
    add_target_args(p_use)

    # apply
    p_apply = subparsers.add_parser("apply", help="auto-detect project type and apply presets")
    p_apply.add_argument("--dry-run", action="store_true", help="show what would be applied")
    add_target_args(p_apply)

    # add
    p_add = subparsers.add_parser("add", help="add skills from a GitHub repo")
    p_add.add_argument("repo", help="repo in owner/repo format")
    add_target_args(p_add)

    # update
    p_update = subparsers.add_parser("update", help="update repo(s) and refresh links")
    p_update.add_argument("repo", nargs="?", help="specific repo to update (optional)")
    group = p_update.add_mutually_exclusive_group()
    group.add_argument(
        "-g", "--global", dest="g", action="store_true", help="target global settings"
    )
    group.add_argument(
        "-p", "--project", dest="p", action="store_true", help="target project settings"
    )

    args = parser.parse_args()

    handlers = {
        "builtins": cmd_builtins,
        "use": cmd_use,
        "apply": cmd_apply,
        "add": cmd_add,
        "update": cmd_update,
    }
    handlers[args.command](args)


if __name__ == "__main__":
    main()
