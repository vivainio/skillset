# skillset

Manage AI skills and permissions across projects for Claude Code.

## Install

```bash
uv tool install skillset
```

Or with pip:

```bash
pip install skillset
```

## Usage

### Apply permissions

```bash
skillset apply              # auto-detect project type (git, python, node, etc.)
skillset apply python git   # apply specific presets
skillset apply --dry-run    # preview what would be applied
```

Built-in presets: `developer`, `git`, `node`, `python`, `docker`, `k8s`

### Save and reuse permissions

```bash
skillset save mypreset      # save current project permissions
skillset apply mypreset     # apply in another project
```

### Add skills from GitHub

```bash
skillset add owner/repo     # add to project .claude/skills/
skillset add owner/repo -g  # add to global ~/.claude/skills/
```

### List installed skills and presets

```bash
skillset list
```

### Update cached repos

```bash
skillset update             # pull all cached repos
skillset update owner/repo  # update specific repo
```

## How it works

- Permissions are written to `.claude/settings.local.json` (project-local, not committed)
- Skills are symlinked (Linux/Mac) or junctioned (Windows) from cached repos
- User presets stored in `~/.config/skillset/presets/`
- Repo cache in `~/.cache/skillset/repos/`

## License

MIT
