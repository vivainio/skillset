---
name: skillset
description: Manage AI skills and commands across projects with the skillset CLI. Use when the user wants to add, remove, search, list, or update Claude Code skills/commands from a GitHub repo or local directory, mentions "skillset", "skillset.yaml", or asks to install/discover a skill.
---

# skillset - Skill Manager CLI

Manages Claude Code (and Copilot) skills and slash commands, symlinked or copied from GitHub repos or local directories. See https://github.com/vivainio/skillset for source.

**Scope:** commands auto-detect scope -- if a `skillset.yaml` is found in the current directory or a parent, skills install to the project (`.claude/skills/`); otherwise they install globally (`~/.claude/skills/`). Pass `-g`/`--global` to force global scope.

**Start here:** `skillset search <term>` to find a skill across everything already cached, `skillset add owner/repo` to install skills from a repo.

## Commands

```bash
# Add skills from a GitHub repo (owner/repo, full URL, or local path)
skillset add vivainio/agent-skills                    # all skills from repo (prompts to select)
skillset add vivainio/agent-skills -g                  # force global install
skillset add vivainio/agent-skills -s zaira            # only the zaira skill
skillset add vivainio/agent-skills -s zaira -s other   # multiple specific skills
skillset add vivainio/agent-skills -s doc-%            # glob pattern -- % is a shell-safe wildcard, no quoting needed
skillset add vivainio/agent-skills -p extra-skills     # skills from a subdirectory only
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

# Search skills across every cached repo and editable source (local, offline)
skillset search jira                    # name/description contains "jira"
skillset search jenkins build           # all terms must match (AND)
skillset search jira-%                  # glob: name starting with "jira-"
skillset search %config%                # glob: "config" anywhere in name or description

# Remove skills
skillset remove zaira           # remove from detected scope
skillset remove zaira -g        # remove from global skills
skillset remove ai-%            # glob pattern -- % is a shell-safe wildcard, no quoting needed
skillset remove -i              # interactive fzf selection

# List installed skills, commands, and cached repos
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

`skillset update` applies this file: pulls each repo, links `enabled`, removes `disabled`. New skills not yet listed in either list are reported (local config) or prompted interactively (global config) unless `-y`/`-n` is passed.

## How it works

- Skills/commands are symlinked (Linux/Mac) or junctioned (Windows) from cached repos, not copied, unless `--copy`/`--no-cache`/`--snapshot`.
- Repo cache lives in `~/.cache/skillset/repos/`.
- `--fetch` is the way to get a repo into the cache (and registered in `skillset.yaml` with nothing enabled) purely so `skillset search` can find its skills later, without installing anything yet.
