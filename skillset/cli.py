"""CLI for managing AI skills across projects."""

from typing import Annotated

import typer

from skillset.commands import (
    cmd_add,
    cmd_clean,
    cmd_init,
    cmd_install_skills,
    cmd_list,
    cmd_profile,
    cmd_remove,
    cmd_remove_all,
    cmd_search,
    cmd_update,
)

app = typer.Typer(
    name="skillset",
    help="Manage AI skills across projects",
    no_args_is_help=True,
)


def _version_callback(value: bool) -> None:
    if value:
        from skillset import __version__

        print(f"skillset {__version__}")
        raise typer.Exit()


@app.callback()
def _main(
    version: Annotated[
        bool | None,
        typer.Option("--version", callback=_version_callback, is_eager=True, help="Show version"),
    ] = None,
) -> None:
    """Manage AI skills across projects."""


@app.command("list")
def list_cmd(
    prune: Annotated[bool, typer.Option(help="Remove broken links")] = False,
    available: Annotated[
        bool,
        typer.Option(help="List skills in cached repos/editable sources that aren't installed"),
    ] = False,
) -> None:
    """List installed skills and commands."""
    cmd_list(prune=prune, available=available)


@app.command()
def add(
    repo: Annotated[str | None, typer.Argument(help="Repo in owner/repo format")] = None,
    global_: Annotated[
        bool,
        typer.Option("-g", "--global", help="Install skills globally"),
    ] = False,
    skill: Annotated[
        list[str] | None,
        typer.Option(
            "-s",
            "--skill",
            help="Add only this skill by name or glob (repeatable); % is a shell-safe wildcard",
        ),
    ] = None,
    agent: Annotated[
        list[str] | None,
        typer.Option(
            "-a",
            "--agent",
            help="Add only this agent by name or glob (repeatable); % is a shell-safe wildcard",
        ),
    ] = None,
    command: Annotated[
        list[str] | None,
        typer.Option(
            "-c",
            "--command",
            help="Add only this command by name or glob (repeatable); % is a shell-safe wildcard",
        ),
    ] = None,
    subpath: Annotated[
        str | None,
        typer.Option("-p", "--path", help="Subdirectory within the repo to use as root"),
    ] = None,
    ref: Annotated[
        str | None,
        typer.Option("--ref", help="Git ref (branch, tag, or commit) to check out"),
    ] = None,
    copy: Annotated[
        bool,
        typer.Option("--copy", help="Copy files instead of symlinking (for Windows without admin)"),
    ] = False,
    no_cache: Annotated[
        bool,
        typer.Option("--no-cache", help="Clone to a temp dir, copy skills, then clean up"),
    ] = False,
    trial: Annotated[
        bool,
        typer.Option("--try", help="Install on trial basis (remove with 'clean')"),
    ] = False,
    interactive: Annotated[
        bool,
        typer.Option("-i", "--interactive", help="Select skills interactively with fzf"),
    ] = False,
    force: Annotated[
        bool,
        typer.Option("--force", help="Override an existing pinned ref in skillset.yaml"),
    ] = False,
    snapshot: Annotated[
        bool,
        typer.Option(
            "--snapshot",
            help="Copy skills frozen at current HEAD; skipped by 'update'",
        ),
    ] = False,
    unsnapshot: Annotated[
        bool,
        typer.Option(
            "--unsnapshot",
            help="Drop snapshot/ref pin and switch back to live links",
        ),
    ] = False,
    fetch: Annotated[
        bool,
        typer.Option(
            "--fetch",
            help="Clone/cache the repo and register it with no skills enabled -- link nothing now",
        ),
    ] = False,
) -> None:
    """Add skills from a GitHub repo. Installs locally if skillset.yaml is found in path."""
    cmd_add(
        repo=repo,
        g=global_,
        skills=skill,
        agents=agent,
        commands=command,
        subpath=subpath,
        ref=ref,
        copy=copy,
        no_cache=no_cache,
        trial=trial,
        interactive=interactive,
        force=force,
        snapshot=snapshot,
        unsnapshot=unsnapshot,
        fetch=fetch,
    )


@app.command("install-skills")
def install_skills() -> None:
    """Install skillset's own global usage-guide skill."""
    cmd_install_skills()


@app.command()
def profile(
    name: Annotated[
        str | None,
        typer.Argument(help="Profile to activate; omit to open the interactive menu"),
    ] = None,
) -> None:
    """Save, switch, and delete global skill profiles."""
    cmd_profile(name=name)


@app.command()
def search(
    query: Annotated[
        list[str],
        typer.Argument(
            help="Search term(s) -- all must match a skill's name or description; "
            "% is a shell-safe wildcard"
        ),
    ],
) -> None:
    """Search skill names/descriptions across cached repos and editable sources."""
    cmd_search(query=query)


@app.command()
def update(
    file: Annotated[
        str | None,
        typer.Option(help="Path to skillset.yaml"),
    ] = None,
    global_: Annotated[
        bool, typer.Option("-g", "--global", help="Update from global ~/.claude/skillset.yaml")
    ] = False,
    yes: Annotated[
        bool,
        typer.Option("-y", "--yes", help="Accept all new skills without prompting"),
    ] = False,
    no: Annotated[
        bool,
        typer.Option("-n", "--no", help="Ignore all new skills without prompting"),
    ] = False,
    repair: Annotated[
        bool,
        typer.Option("--repair", help="Repair duplicate or missing editable repository sources"),
    ] = False,
) -> None:
    """Update skills from skillset.yaml -- pull repos, link enabled, unlink disabled."""
    if yes and no:
        typer.echo("--yes and --no are mutually exclusive", err=True)
        raise typer.Exit(1)
    new = "yes" if yes else "no" if no else "ask"
    cmd_update(file=file, g=global_, new=new, repair=repair)


@app.command()
def init(
    global_: Annotated[
        bool, typer.Option("-g", "--global", help="Create global ~/.claude/skillset.yaml")
    ] = False,
) -> None:
    """Create a skillset.yaml file. Default: local at git root. --global for ~/.claude/."""
    cmd_init(g=global_)


@app.command()
def clean(
    global_: Annotated[
        bool, typer.Option("-g", "--global", help="Clean global trial skills")
    ] = False,
) -> None:
    """Remove all trial skills."""
    cmd_clean(g=global_)


@app.command()
def remove(
    name: Annotated[
        str | None,
        typer.Argument(help="Skill name or glob (e.g. bs-%), or owner/repo to remove a whole repo"),
    ] = None,
    global_: Annotated[
        bool,
        typer.Option("-g", "--global", help="Remove from global skills"),
    ] = False,
    interactive: Annotated[
        bool,
        typer.Option("-i", "--interactive", help="Select skills to remove with fzf"),
    ] = False,
    all_: Annotated[
        bool,
        typer.Option(
            "--all",
            help="Remove every registered repo and wipe the whole (machine-wide) repo cache "
            "for a fresh start",
        ),
    ] = False,
) -> None:
    """Remove a skill, or a whole repo (owner/repo) -- links, skillset.yaml entry, and cache."""
    if all_:
        if name or interactive:
            typer.echo("--all cannot be combined with a name or -i", err=True)
            raise typer.Exit(1)
        cmd_remove_all(g=global_)
        return
    cmd_remove(name=name, g=global_, interactive=interactive)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
