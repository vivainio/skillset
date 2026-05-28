# skillset

Manage AI skills across projects for Claude Code.

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

### Add skills from GitHub

```bash
skillset add vivainio/agent-skills                    # all skills from repo
skillset add vivainio/agent-skills -g                 # force global install even if local skillset.yaml file is found
skillset add vivainio/agent-skills -s zaira           # only the zaira skill
skillset add vivainio/agent-skills -s zaira -s other  # multiple specific skills
skillset add vivainio/agent-skills -p extra-skills    # skills from extra-skills/ subdirectory only
```

You can also pass a full GitHub URL:

```bash
skillset add https://github.com/vivainio/agent-skills
skillset add https://github.com/vivainio/agent-skills/tree/main/extra-skills
```

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
skillset remove "ai-*"         # glob patterns supported
```

### List installed skills

```bash
skillset list           # list all installed skills, commands, and cached repos
skillset list --prune   # also remove broken links
```

### Initialize skillset.yaml

```bash
skillset init           # create skillset.yaml at git root (local)
skillset init -g        # create ~/.claude/skillset.yaml (global)
```

### Declarative config (skillset.yaml)

Manage skills declaratively in a `skillset.yaml` file — globally at `~/.claude/skillset.yaml`, or per-project at your repo root. Each entry under `skills:` is keyed by `owner/repo`:

```yaml
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

`update` applies the config: it processes `links:`, pulls each repo, links skills in `enabled`, removes those in `disabled`, and prompts for any new skills in the repo that aren't yet listed in either list. `enabled: ["*"]` links every skill (minus anything in `disabled`). Any entry containing `*`, `?`, or `[` is treated as an fnmatch glob against available skill names. Snapshot entries are skipped entirely.

```bash
skillset update                              # apply local skillset.yaml if found, otherwise global
skillset update -g                           # apply global ~/.claude/skillset.yaml
skillset update --file path/to/skillset.yaml # apply a specific file
skillset update -y                           # accept all new skills without prompting
skillset update -n                           # ignore all new skills without prompting
```

## How it works

- Skills are symlinked (Linux/Mac) or junctioned (Windows) from cached repos
- Repo cache in `~/.cache/skillset/repos/`

## Comparison with Vercel's `npx skills`

Vercel's [`skills`](https://github.com/vercel-labs/skills) CLI is a cross-agent package manager with a central registry at [skills.sh](https://skills.sh). Both tools manage SKILL.md-based skills from GitHub repos, but they differ in scope and focus.

|                 | **skillset**                           | **Vercel `npx skills`**               |
| --------------- | -------------------------------------- | ------------------------------------- |
| Target agents   | Claude Code                            | 40+ (Claude, Cursor, Codex, Copilot…) |
| Slash commands  | Links `/commands` from repos           | No                                    |
| Skill discovery | n/a                                    | Central registry (89K+ skills)        |
| Install method  | `pip` / `uv tool install` / `uvx`      | `npx`                                 |
| Scope default   | Project if available, Global otherwise | Project                               |

**skillset** is a Claude Code power-user tool for managing skills. Vercel's CLI is a cross-agent marketplace. The two are complementary — discover skills via Vercel's registry, install and manage them via skillset.

## License

MIT
