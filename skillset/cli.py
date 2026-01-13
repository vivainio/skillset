"""CLI for managing AI skills and permissions across projects."""

import json
import subprocess
from pathlib import Path

import click

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


def parse_repo_spec(spec: str) -> tuple[str, str]:
    """Parse 'owner/repo' into (owner, repo)."""
    parts = spec.strip().split("/")
    if len(parts) != 2:
        raise click.ClickException(f"Invalid repo format: {spec}. Use 'owner/repo'")
    return parts[0], parts[1]


def get_repo_dir(owner: str, repo: str) -> Path:
    """Get the cache directory for a repo."""
    return get_cache_dir() / owner / repo


def clone_or_pull(owner: str, repo: str) -> Path:
    """Clone repo if not exists, or pull if it does. Returns repo path."""
    repo_dir = get_repo_dir(owner, repo)
    repo_url = f"https://github.com/{owner}/{repo}.git"

    if repo_dir.exists():
        click.echo(f"Updating {owner}/{repo}...")
        subprocess.run(["git", "pull"], cwd=repo_dir, check=True, capture_output=True)
    else:
        click.echo(f"Cloning {owner}/{repo}...")
        repo_dir.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "clone", repo_url, str(repo_dir)], check=True, capture_output=True)

    return repo_dir


def find_skills(repo_dir: Path) -> list[Path]:
    """Find skill directories in a repo. A skill is a dir with a markdown file."""
    skills = []
    for md_file in repo_dir.glob("**/*.md"):
        # Skip hidden dirs and repo root README
        if any(part.startswith(".") for part in md_file.relative_to(repo_dir).parts):
            continue
        if md_file.parent == repo_dir and md_file.name.lower() == "readme.md":
            continue
        # The skill is the directory containing the markdown file
        skill_dir = md_file.parent
        if skill_dir not in skills and skill_dir != repo_dir:
            skills.append(skill_dir)
    return skills


def link_skills(repo_dir: Path, target_dir: Path) -> list[str]:
    """Symlink skill directories from repo to target skills dir. Returns list of linked names."""
    target_dir.mkdir(parents=True, exist_ok=True)

    linked = []
    skills = find_skills(repo_dir)

    for skill_dir in skills:
        skill_name = skill_dir.name
        link_path = target_dir / skill_name

        # Remove existing symlink if present
        if link_path.is_symlink():
            link_path.unlink()
        elif link_path.exists():
            click.echo(f"  Skipping {skill_name}: already exists (not a symlink)")
            continue

        link_path.symlink_to(skill_dir)
        linked.append(skill_name)

    return linked


def get_global_settings_path() -> Path:
    """Get global Claude settings path."""
    return Path.home() / ".claude" / "settings.json"


def get_project_settings_path() -> Path:
    """Get project-local Claude settings path."""
    return Path.cwd() / ".claude" / "settings.json"


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


def merge_permissions(repo_dir: Path, settings_path: Path) -> list[str]:
    """Merge repo permissions into target settings. Returns list of merged keys."""
    repo_perms = find_repo_permissions(repo_dir)
    if not repo_perms:
        return []

    existing = load_settings(settings_path)
    merged = deep_merge(existing, repo_perms)
    save_settings(settings_path, merged)

    return list(repo_perms.keys())


def load_preset(name: str) -> dict | None:
    """Load a preset by name."""
    preset_path = get_presets_dir() / f"{name}.json"
    if preset_path.exists():
        return json.loads(preset_path.read_text())
    return None


def save_preset(name: str, config: dict) -> None:
    """Save a preset."""
    presets_dir = get_presets_dir()
    presets_dir.mkdir(parents=True, exist_ok=True)
    preset_path = presets_dir / f"{name}.json"
    preset_path.write_text(json.dumps(config, indent=2))


def load_project_settings(project_dir: Path) -> dict:
    """Load Claude settings for a project."""
    settings_path = project_dir / CLAUDE_SETTINGS_FILE
    if settings_path.exists():
        return json.loads(settings_path.read_text())
    return {}


def save_project_settings(project_dir: Path, settings: dict) -> None:
    """Save Claude settings for a project."""
    settings_path = project_dir / CLAUDE_SETTINGS_FILE
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(json.dumps(settings, indent=2))


@click.group()
def main() -> None:
    """Manage AI skills and permissions across projects."""
    pass


@main.command()
def list() -> None:
    """List available permission presets."""
    presets_dir = get_presets_dir()
    if not presets_dir.exists():
        click.echo("No presets found. Create one with 'skillset save <name>'")
        return

    presets = list(presets_dir.glob("*.json"))
    if not presets:
        click.echo("No presets found. Create one with 'skillset save <name>'")
        return

    click.echo("Available presets:")
    for preset in sorted(presets):
        click.echo(f"  - {preset.stem}")


@main.command()
@click.argument("name")
@click.option(
    "--project",
    "-p",
    type=click.Path(exists=True),
    default=".",
    help="Project directory (default: current)",
)
def save(name: str, project: str) -> None:
    """Save current project's Claude settings as a preset."""
    project_dir = Path(project).resolve()
    settings = load_project_settings(project_dir)

    if not settings:
        click.echo(f"No Claude settings found in {project_dir}")
        return

    save_preset(name, settings)
    click.echo(f"Saved preset '{name}'")


@main.command()
@click.argument("name")
@click.option(
    "--project",
    "-p",
    type=click.Path(exists=True),
    default=".",
    help="Project directory (default: current)",
)
@click.option(
    "--merge/--replace",
    default=True,
    help="Merge with existing settings (default) or replace entirely",
)
def apply(name: str, project: str, merge: bool) -> None:
    """Apply a permission preset to a project."""
    preset = load_preset(name)
    if not preset:
        click.echo(f"Preset '{name}' not found")
        return

    project_dir = Path(project).resolve()

    if merge:
        existing = load_project_settings(project_dir)
        # Deep merge: preset values override existing
        merged = deep_merge(existing, preset)
        save_project_settings(project_dir, merged)
    else:
        save_project_settings(project_dir, preset)

    click.echo(f"Applied preset '{name}' to {project_dir}")


@main.command()
@click.argument("name")
def show(name: str) -> None:
    """Show contents of a preset."""
    preset = load_preset(name)
    if not preset:
        click.echo(f"Preset '{name}' not found")
        return

    click.echo(json.dumps(preset, indent=2))


@main.command()
@click.argument("name")
def delete(name: str) -> None:
    """Delete a preset."""
    preset_path = get_presets_dir() / f"{name}.json"
    if not preset_path.exists():
        click.echo(f"Preset '{name}' not found")
        return

    preset_path.unlink()
    click.echo(f"Deleted preset '{name}'")


@main.command()
@click.argument("repo")
@click.option(
    "--global",
    "-g",
    "use_global",
    is_flag=True,
    help="Install to global skills (~/.claude/skills/)",
)
@click.option(
    "--project",
    "-p",
    "use_project",
    is_flag=True,
    help="Install to project skills (.claude/skills/)",
)
def add(repo: str, use_global: bool, use_project: bool) -> None:
    """Add skills and permissions from a GitHub repo."""
    if use_global and use_project:
        raise click.ClickException("Cannot use both --global and --project")
    if not use_global and not use_project:
        raise click.ClickException("Must specify --global or --project")

    owner, repo_name = parse_repo_spec(repo)
    repo_dir = clone_or_pull(owner, repo_name)

    # Link skills
    skills_dir = get_global_skills_dir() if use_global else get_project_skills_dir()
    linked = link_skills(repo_dir, skills_dir)

    if linked:
        click.echo(f"Linked {len(linked)} skill(s) to {skills_dir}:")
        for skill_name in sorted(linked):
            click.echo(f"  - {skill_name}")

    # Merge permissions
    settings_path = get_global_settings_path() if use_global else get_project_settings_path()
    merged_keys = merge_permissions(repo_dir, settings_path)

    if merged_keys:
        click.echo(f"Merged permissions into {settings_path}:")
        for key in sorted(merged_keys):
            click.echo(f"  - {key}")

    if not linked and not merged_keys:
        click.echo("No skills or permissions found in repo")


@main.command()
@click.argument("repo", required=False)
@click.option("--global", "-g", "use_global", is_flag=True, help="Update global skills")
@click.option("--project", "-p", "use_project", is_flag=True, help="Update project skills")
def update(repo: str | None, use_global: bool, use_project: bool) -> None:
    """Update repo(s) and refresh symlinks and permissions."""
    cache_dir = get_cache_dir()

    if repo:
        if use_global and use_project:
            raise click.ClickException("Cannot use both --global and --project")
        if not use_global and not use_project:
            raise click.ClickException("Must specify --global or --project")

        owner, repo_name = parse_repo_spec(repo)
        repo_dir = get_repo_dir(owner, repo_name)
        if not repo_dir.exists():
            click.echo(f"Repo {repo} not installed. Use 'skillset add {repo}' first.")
            return
        clone_or_pull(owner, repo_name)

        # Refresh skills
        skills_dir = get_global_skills_dir() if use_global else get_project_skills_dir()
        linked = link_skills(repo_dir, skills_dir)
        click.echo(f"Updated {len(linked)} skill(s)")

        # Refresh permissions
        settings_path = get_global_settings_path() if use_global else get_project_settings_path()
        merged_keys = merge_permissions(repo_dir, settings_path)
        if merged_keys:
            click.echo(f"Refreshed {len(merged_keys)} permission key(s)")
    else:
        # Update all cached repos (git pull only)
        if not cache_dir.exists():
            click.echo("No repos installed")
            return

        for owner_dir in cache_dir.iterdir():
            if not owner_dir.is_dir():
                continue
            for repo_dir in owner_dir.iterdir():
                if not repo_dir.is_dir():
                    continue
                owner = owner_dir.name
                repo_name = repo_dir.name
                clone_or_pull(owner, repo_name)
        click.echo("All repos updated (use --global/-g or --project/-p to refresh links)")


def deep_merge(base: dict, override: dict) -> dict:
    """Deep merge two dictionaries, with override taking precedence."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        elif key in result and isinstance(result[key], list) and isinstance(value, list):
            # For lists, combine unique values
            result[key] = list(set(result[key] + value))
        else:
            result[key] = value
    return result


if __name__ == "__main__":
    main()
