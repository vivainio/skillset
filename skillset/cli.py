"""CLI for managing AI skills across projects."""

from typing import Annotated

import typer

from skillset.commands import (
    cmd_add,
    cmd_clean,
    cmd_init,
    cmd_list,
    cmd_remove,
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
) -> None:
    """List installed skills and commands."""
    cmd_list(prune=prune)


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
            help="Add only this skill by name or glob (repeatable); use % for * to skip quoting",
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
) -> None:
    """Add skills from a GitHub repo. Installs locally if skillset.yaml is found in path."""
    cmd_add(
        repo=repo,
        g=global_,
        skills=skill,
        subpath=subpath,
        ref=ref,
        copy=copy,
        no_cache=no_cache,
        trial=trial,
        interactive=interactive,
        force=force,
        snapshot=snapshot,
        unsnapshot=unsnapshot,
    )


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
) -> None:
    """Update skills from skillset.yaml -- pull repos, link enabled, unlink disabled."""
    if yes and no:
        typer.echo("--yes and --no are mutually exclusive", err=True)
        raise typer.Exit(1)
    new = "yes" if yes else "no" if no else "ask"
    cmd_update(file=file, g=global_, new=new)


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
        str | None, typer.Argument(help="Skill name or glob (e.g. bs-% or 'bs-*')")
    ] = None,
    global_: Annotated[
        bool,
        typer.Option("-g", "--global", help="Remove from global skills"),
    ] = False,
    interactive: Annotated[
        bool,
        typer.Option("-i", "--interactive", help="Select skills to remove with fzf"),
    ] = False,
) -> None:
    """Remove a skill by name. Removes from local scope if skillset.yaml is found in path."""
    cmd_remove(name=name, g=global_, interactive=interactive)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
