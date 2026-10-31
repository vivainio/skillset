# Getting started

## Install

```bash
uv tool install skillset
# or
pip install skillset
```

For development:

```bash
uv tool install . -e
```

## Scope

Commands detect scope automatically. If a `skillset.yaml` is found in the current
directory or any parent, skills install to the project (`.claude/skills/`). Otherwise
they install globally (`~/.claude/skills/`). Use `-g` / `--global` to force global scope.

## Teach Claude the CLI

```bash
skillset install-skills
```

Installs a bundled `SKILL.md` (shipped with the package, no network access) that
documents skillset's own commands, so Claude Code can use `skillset` correctly without
this documentation pasted into context. It always installs globally and also links
supported agents' global skill directories.

## First steps

```bash
skillset add vivainio/agent-skills      # clone and link every skill in the repo
skillset list                           # see what is installed
skillset init                           # create a skillset.yaml at the git root
```
