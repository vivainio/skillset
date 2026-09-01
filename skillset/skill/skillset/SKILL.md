---
name: skillset
description: Manage AI skills, commands, and agents across projects with the skillset CLI. Use when the user wants to add, remove, search, list, or update Claude Code skills, commands, or agents from a GitHub repo or local directory, mentions "skillset", "skillset.yaml", or asks to install or discover one.
---

# skillset - Skill Manager CLI

Manages Claude Code (and Copilot) skills, slash commands, and Claude Code agents, symlinked or copied from GitHub repos or local directories. See https://github.com/vivainio/skillset for source.

**Scope:** management commands auto-detect scope -- if a `skillset.yaml` is found in the current directory or a parent, artifacts install under the project's `.claude/`; otherwise they install under `~/.claude/`. Pass `-g`/`--global` to force global scope. `install-skills` always installs globally.

**Start here:** `skillset search <term>` to find a skill across cached, editable, and unmanaged sources, `skillset add owner/repo` to install skills from a repo.

## Commands

```bash
# Add skills from a GitHub repo (owner/repo, full URL, or local path)
skillset add vivainio/agent-skills                    # all skills from repo (prompts to select)
skillset add vivainio/agent-skills -g                  # force global install
skillset add vivainio/agent-skills -s zaira            # only the zaira skill
skillset add vivainio/agent-skills -s zaira -s other   # multiple specific skills
skillset add vivainio/agent-skills -s doc-%            # glob pattern -- % is a shell-safe wildcard, no quoting needed
skillset add owner/repo -a reviewer                    # only this agent
skillset add owner/repo -a review-% -a tester          # repeatable agent names/globs
skillset add vivainio/agent-skills -p extra-skills     # discover artifacts only in this subtree
skillset add owner/repo -p package/agents -a review-%  # -p may point directly at an agents directory
skillset add https://github.com/vivainio/agent-skills
skillset add https://github.com/vivainio/agent-skills/tree/main/extra-skills
skillset add /path/to/skills-dir                       # local dir; registered as editable
skillset add zaira                                     # look up a skill by name across all known sources
skillset add vivainio/agent-skills -i                  # interactive fzf selection
skillset add vivainio/agent-skills --copy               # copy files instead of symlinking (Windows w/o admin)
skillset add vivainio/agent-skills --no-cache           # clone to temp dir, copy, then clean up
skillset add vivainio/agent-skills --try                # install as trial (see 'skillset clean')
skillset add vivainio/agent-skills --ref v1.2.0         # pin to a branch/tag/commit
skillset add vivainio/agent-skills -s zaira --snapshot  # freeze the skill at current HEAD, 'update' skips it
skillset add vivainio/agent-skills -s zaira --unsnapshot  # convert a snapshot back to a live link
skillset add owner/repo --fetch                         # clone/cache only, register with no skills enabled -- link nothing yet

# Search cached, editable, installed unmanaged, and saved unmanaged skills (local, offline)
skillset search jira                    # name/description contains "jira"
skillset search jenkins build           # all terms must match (AND)
skillset search jira-%                  # glob: name starting with "jira-"
skillset search %config%                # glob: "config" anywhere in name or description

# Remove skills
skillset remove zaira           # remove from detected scope
skillset remove zaira -g        # remove from global skills
skillset remove ai-%            # glob pattern -- % is a shell-safe wildcard, no quoting needed
skillset remove -i              # interactive fzf selection

# Remove a whole repo -- a name containing "/" is treated as owner/repo, not a skill name:
# unlinks every skill/command/agent sourced from it, drops its skillset.yaml entry, deletes the cached clone
skillset remove JuliusBrussee/caveman

# Remove every registered repo, then wipe the entire (machine-wide) repo cache dir --
# also deletes cached clones from other projects and untracked trial repos.
# Use for a completely fresh start.
skillset remove --all
skillset remove --all -g        # global skillset.yaml

# List installed skills, commands, agents, and cached repos
skillset list
skillset list --prune           # also remove broken symlinks

# Update from skillset.yaml -- pulls repos, links 'enabled', unlinks 'disabled'
skillset update                 # local skillset.yaml if found, else global
skillset update -g              # force global ~/.claude/skillset.yaml
skillset update --file path/to/skillset.yaml
skillset update -y              # accept all newly-discovered skills without prompting
skillset update -n              # ignore all newly-discovered skills without prompting

# Trial cleanup
skillset clean                  # remove all trial skills and their cached repos
skillset clean -g               # global trial skills only

# Global skill profiles
skillset profile                # interactive switch/save/delete menu (fzf or numbered fallback)
skillset profile work           # activate a saved profile directly

# Initialize skillset.yaml
skillset init                   # create at git root (local, project scope)
skillset init -g                # create ~/.claude/skillset.yaml (global scope)
```

## skillset.yaml

Declarative config, keyed by `owner/repo` under `skills:`:

```yaml
skills:
  vivainio/agent-skills:
    enabled: ["*"]                  # all skills

  vivainio/agent-skills:
    enabled: [zaira]                # selective
    disabled: [some-other]

  vivainio/agent-skills:
    enabled: ["doc-*"]              # glob patterns
    disabled: [doc-draft]
    agents: ["review-*", tester]    # flat agent selector list; globs supported

  owner/repo:
    enabled: ["*"]
    agents: []                      # install no agents

  vivainio/agent-skills:
    path: extra-skills              # skills from a subdirectory
    enabled: ["*"]

  vivainio/agent-skills:
    copy: true                      # copy instead of symlink
    enabled: ["*"]

  my-lib:
    path: extra-skills              # editable: points at a local checkout
    editable: true
    source: ~/repos/agent-skills
    enabled: ["*"]

links:
  specs: ../project-docs/specs       # arbitrary cross-repo symlinks
```

`skillset update` applies this file: pulls each repo, links `enabled`, removes `disabled`, and synchronizes agents using the flat `agents` selector list. With no `agents` key, all discovered agents are installed; `agents: []` installs none. New skills not yet listed in either skill list are reported (local config) or prompted interactively (global config) unless `-y`/`-n` is passed.

## How it works

- Skills are identified by `SKILL.md` anywhere below the selected source root. Commands are Markdown below `commands/`; agents are Markdown below `agents/`, including canonical `.claude/agents/` sources.
- Agent names are install-relative paths without `.md`: `agents/review/security.md` is `review/security`. Nested paths are preserved in `.claude/agents/`.
- `-p` changes the discovery root for skills, commands, and agents. `-a`/`--agent` is repeatable, accepts the same `*`/`%` globs as skills, and replaces the source's prior agent selector list.
- Skills/commands/agents are symlinked (Linux/Mac) or junctioned where applicable on Windows from cached repos, not copied, unless `--copy`/`--no-cache`/`--snapshot`.
- Repository sources live in `~/.local/share/skillset/repos/` on Linux,
  `~/Library/Application Support/skillset/repos/` on macOS, and
  `%LOCALAPPDATA%\skillset\repos` on Windows. Legacy
  `~/.cache/skillset/repos/` clones remain supported.
- `--fetch` is the way to get a repo into the cache (and registered in `skillset.yaml` with nothing enabled) purely so `skillset search` can find its skills later, without installing anything yet.
