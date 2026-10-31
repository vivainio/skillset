---
icon: lucide/layers
---

# skillset

Manage Claude Code skills, commands and agents across projects.

`skillset` installs, links and syncs `SKILL.md`-based skills from GitHub repos or
local directories into `~/.claude/skills/` (global) or `.claude/skills/`
(project-local). Commands and agents in those repos are linked too.

```bash
uv tool install skillset

skillset add vivainio/agent-skills -s zaira   # link one skill from a repo
skillset search jira                          # find skills in cached repos
skillset get zaira                            # read a skill without installing it
skillset update                               # pull repos, apply skillset.yaml
```

## Why

- **Declarative.** A `skillset.yaml` says which skills, commands and agents you want;
  `skillset update` makes the links match.
- **Live.** Skills are symlinked from a cached clone, so updating the repo updates the
  skill. Use `--snapshot` to freeze one at a commit.
- **Context-friendly.** `skillset get` prints a skill's `SKILL.md` straight from the
  cache, so Claude can read a skill on demand without it being linked globally and
  listed in every session.

Start with [Getting started](getting-started.md).
