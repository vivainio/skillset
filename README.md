# skillset

Manage AI skills, commands, and agents across projects for Claude Code.

## Install

```bash
uv tool install skillset
```

Or with pip:

```bash
pip install skillset
```

### Install as developer

```bash
uv tool install . -e
```

## Usage

By default, commands detect scope automatically: if a `skillset.yaml` is found in the current directory or any parent, skills install to the project (`.claude/skills/`). Otherwise, they install globally (`~/.claude/skills/`). Use `-g` / `--global` to force global scope.

### Install skillset's own skill

```bash
skillset install-skills       # teach Claude Code the skillset CLI itself
```

Installs a bundled `SKILL.md` (ships with the package, no network access) that
documents the `skillset` CLI's own commands, so Claude Code can use `skillset`
correctly without needing this README pasted into context. This command always
installs globally and also links supported agents' global skill directories.

### Add skills from GitHub

```bash
skillset add vivainio/agent-skills                    # all skills from repo
skillset add vivainio/agent-skills -g                 # force global install even if local skillset.yaml file is found
skillset add vivainio/agent-skills -s zaira           # only the zaira skill
skillset add vivainio/agent-skills -s zaira -s other  # multiple specific skills
skillset add vivainio/agent-skills -p extra-skills    # discover only within this subtree
skillset add owner/repo -a reviewer -a test-%         # select agents by name/glob
skillset add owner/repo -p package/agents -a review-% # -p may be an agents directory
```

Agent definitions are installed alongside skills and commands. Markdown files
below any `agents/` directory are linked to `.claude/agents/` (or
`~/.claude/agents/` globally), preserving paths below the `agents/` directory.
The `-p` option limits discovery of skills, commands, and agents to that subtree;
it may also point directly at an `agents/` directory. Canonical
`.claude/agents/` source directories are supported.

Agent selectors use install-relative names without `.md`; for example,
`agents/review/security.md` is selected as `review/security`. `%` is the
shell-safe alias for `*`. Selections persist independently from skills:

```yaml
skills:
  owner/repo:
    enabled: ["*"]
    agents: ["review-*"]
```

With no `agents` key, all discovered agents are installed. `agents: []`
installs none. Explicit selectors are replacement-based: running `add -a ...`
again replaces that source's previous agent selection.

You can also pass a full GitHub URL:

```bash
skillset add https://github.com/vivainio/agent-skills
skillset add https://github.com/vivainio/agent-skills/tree/main/extra-skills
```

### Fetch a repo without linking artifacts

```bash
skillset add vivainio/agent-skills --fetch
```

`--fetch` clones/caches the repo and registers it in `skillset.yaml` with
`enabled: []` (its current skills go into `disabled`) and `agents: []`, but
links nothing.
Useful for pulling a repo into the local cache -- e.g. to search or browse
its skills later -- without installing any of them yet. A later
`skillset update` will only prompt about skills added upstream after the
fetch, not the ones that already existed when you fetched.

### Copy instead of symlink

```bash
skillset add vivainio/agent-skills --copy       # copy files instead of symlinking
skillset add vivainio/agent-skills --no-cache   # clone to temp dir, copy, then clean up
```

`--copy` is useful on Windows without admin privileges. `--no-cache` avoids keeping a local clone.

### Snapshot a skill (frozen at a commit)

```bash
skillset add vivainio/agent-skills -s zaira --snapshot
```

`--snapshot` copies the selected skills as-is (implies `--copy`) and pins the
entry in `skillset.yaml` to the resolved HEAD SHA with `snapshot: true`.
`skillset update` skips snapshot entries entirely — no pull, no relink — so
you can mix live skills from one repo with frozen skills from another.

To refresh a snapshot to the latest commit, re-run `skillset add ... --snapshot`
(it auto-overrides the pinned ref). To convert it back to a live entry:

```bash
skillset add vivainio/agent-skills -s zaira --unsnapshot
```

`--unsnapshot` clears `snapshot:` and `ref:` from the yaml entry and replaces
the copied skill directories with live symlinks, so future `skillset update`
runs track the upstream branch again.

### Add skills from a local path

```bash
skillset add /path/to/skills-dir                 # all skills from local dir
skillset add /path/to/skills-dir -s zaira        # specific skill from local dir
skillset add zaira                               # look up by name in all sources
```

Local paths are auto-detected and registered as editable in the global `skillset.yaml` so `skillset update` can find them later. When adding by skill name, all sources (editable entries and cached repos) are searched. If a skill exists in multiple sources, you'll be prompted to choose.

### Try skills temporarily

```bash
skillset add --try vivainio/agent-skills    # install as trial
skillset list                               # trial skills shown with (trial) tag
skillset clean                              # remove all trial skills and their cached repos
skillset clean -g                           # clean global trial skills
skillset add vivainio/agent-skills          # re-add without --try to keep permanently
```

### Remove skills

```bash
skillset remove zaira          # remove from detected scope (local or global)
skillset remove zaira -g       # remove from global skills
skillset remove ai-%           # glob pattern -- % is a shell-safe wildcard, no quoting needed
```

### Remove a whole repo

```bash
skillset remove JuliusBrussee/caveman   # remove its linked skills, skillset.yaml entry, and cached clone
```

A `name` containing `/` is treated as `owner/repo` instead of a skill name:
unlinks every skill/command sourced from it, drops its `skillset.yaml` entry
(if any), and deletes the stored clone from the platform data directory.

### Search cached skills

```bash
skillset search jira            # cached, editable, and unmanaged skills matching "jira"
skillset search jenkins build   # all terms must match (AND)
skillset search jira-%          # glob: name starting with "jira-"
skillset search %config%        # glob: "config" anywhere in name or description
```

A term containing `%` is matched as a glob against the skill name and against
the full name+description text; plain terms fall back to a substring match.

Searches skill names and descriptions across every repo already cloned into
the cache (`skillset add ... --fetch` is a good way to get one in there) plus
any editable sources registered in the global `skillset.yaml`. It's local and
offline -- no registry lookup -- so it only finds skills you've fetched
before.

### List installed skills

```bash
skillset list           # list all installed skills, commands, and cached repos
skillset list --prune   # also remove broken links
```

### Global skill profiles

Save and switch between snapshots of the currently active global skills:

```bash
skillset profile          # interactive menu: switch, save, or delete
skillset profile work     # switch directly to a saved profile
```

The menu uses `fzf` when installed and otherwise shows a numbered terminal
menu. When saving, skillset can optionally include unmanaged skills. Those
skills are moved safely into `~/.claude/.skillset/skills/` and linked back into
the global skills directory. Switching profiles only changes skills known to
profiles; unrelated unmanaged skills are left untouched.

### Initialize skillset.yaml

```bash
skillset init           # create skillset.yaml at git root (local)
skillset init -g        # create ~/.claude/skillset.yaml (global)
```

### Declarative config (skillset.yaml)

Manage skills declaratively in a `skillset.yaml` file — globally at `~/.claude/skillset.yaml`, or per-project at your repo root. Each entry under `skills:` is keyed by `owner/repo`:

```yaml
# names installed outside skillset; update never replaces or removes them
unmanaged: [zenkins]

skills:
  # all skills from repo
  vivainio/agent-skills:
    enabled: ["*"]

  # selective: enable zaira, explicitly skip some-other
  vivainio/agent-skills:
    enabled: [zaira]
    disabled: [some-other]

  # glob patterns: link everything matching a prefix, minus one
  vivainio/agent-skills:
    enabled: ["doc-*"]
    disabled: [doc-draft]

  # skills from a subdirectory
  vivainio/agent-skills:
    path: extra-skills
    enabled: ["*"]

  # copy files instead of symlinking
  vivainio/agent-skills:
    copy: true
    enabled: ["*"]

  # editable: point to a local checkout instead of the cache
  vivainio/agent-skills:
    path: extra-skills
    editable: true
    source: ~/repos/agent-skills
    enabled: ["*"]

# arbitrary cross-repo symlinks (e.g. shared specs from a sibling repo)
links:
  specs: ../project-docs/specs
```

**Editable skills** point to a local checkout instead of the cache. Set `editable: true` with `source` pointing to the local path; use `path` to select a subdirectory within it.

`links:` creates symlinks for cross-repo paths. Warns if a link target is not in `.gitignore`.

### Update

`update` applies the config: it processes `links:`, pulls each repo, links skills in `enabled`, and removes those in `disabled`. New skills in a repo that aren't yet listed in either list are handled by scope: with a local `skillset.yaml` they are only reported (the file is a declaration -- it is never amended without `-y`/`-n`); with the global config you get an interactive add/ignore/select prompt. `enabled: ["*"]` links every skill (minus anything in `disabled`). Any entry containing `*`, `?`, `[`, or `%` is treated as an fnmatch glob against available skill names, where `%` is an alias for `*`. The same glob syntax works on the command line (`add -s`, `remove`); prefer `%` there since `*` is expanded by most shells unless quoted. Snapshot entries are skipped entirely.

```bash
skillset update                              # apply local skillset.yaml if found, otherwise global
skillset update -g                           # apply global ~/.claude/skillset.yaml
skillset update --file path/to/skillset.yaml # apply a specific file
skillset update -y                           # accept all new skills without prompting
skillset update -n                           # ignore all new skills without prompting
skillset update --repair                     # repair editable sources; offer to remove old clones
skillset update --repair -y                  # repair and remove redundant clones without prompting
```

## How it works

- Skills are symlinked (Linux/Mac) or junctioned (Windows) from cached repos
- Repository sources in `~/.local/share/skillset/repos/` on Linux,
  `~/Library/Application Support/skillset/repos/` on macOS, and
  `%LOCALAPPDATA%\skillset\repos` on Windows. Existing clones in the legacy
  `~/.cache/skillset/repos/` location remain supported.
- Global scope honors `CLAUDE_CONFIG_DIR`: when set, `skillset` reads and
  writes `skills/`, `commands/`, `agents/`, and `skillset.yaml` under that
  directory instead of `~/.claude/`, matching whichever Claude Code profile
  the env var points at.

## Comparison with Vercel's `npx skills`

Vercel's [`skills`](https://github.com/vercel-labs/skills) CLI is a cross-agent package manager with a central registry at [skills.sh](https://skills.sh). Both tools manage SKILL.md-based skills from GitHub repos, but they differ in scope and focus.

|                 | **skillset**                           | **Vercel `npx skills`**               |
| --------------- | -------------------------------------- | ------------------------------------- |
| Target agents   | Claude Code                            | 40+ (Claude, Cursor, Codex, Copilot…) |
| Slash commands  | Links `/commands` from repos           | No                                    |
| Skill discovery | Local search over cached repos (`search`) | Central registry (89K+ skills)     |
| Install method  | `pip` / `uv tool install` / `uvx`      | `npx`                                 |
| Scope default   | Project if available, Global otherwise | Project                               |

**skillset** is a Claude Code power-user tool for managing skills. Vercel's CLI is a cross-agent marketplace. The two are complementary — discover skills via Vercel's registry, install and manage them via skillset.

## License

MIT
