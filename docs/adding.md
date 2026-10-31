# Adding skills

## From GitHub

```bash
skillset add vivainio/agent-skills                    # all skills from repo
skillset add vivainio/agent-skills -g                 # force global even if a local skillset.yaml exists
skillset add vivainio/agent-skills -s zaira           # only the zaira skill
skillset add vivainio/agent-skills -s zaira -s other  # several skills
skillset add vivainio/agent-skills -p extra-skills    # discover only within this subtree
skillset add owner/repo -a reviewer -a test-%         # select agents by name/glob
skillset add owner/repo -c run-ci-here -c deploy-%    # select commands by name/glob
```

Full GitHub URLs work too:

```bash
skillset add https://github.com/vivainio/agent-skills
skillset add https://github.com/vivainio/agent-skills/tree/main/extra-skills
```

`%` is a shell-safe alias for `*` in every name/glob argument.

## Agents and commands

Markdown files below any `agents/` directory are linked to `.claude/agents/` (or
`~/.claude/agents/` globally), preserving paths below `agents/`. `-p` limits discovery
of skills, commands and agents to a subtree, and may point directly at an `agents/`
directory. Canonical `.claude/agents/` source directories are supported.

Agent selectors use install-relative names without `.md`: `agents/review/security.md`
is selected as `review/security`. `-c`/`--command` filters commands the same way.
Selections persist in `skillset.yaml`:

```yaml
skills:
  owner/repo:
    enabled: ["*"]
    agents: ["review-*"]
    commands: ["run-ci-here", "deploy-*"]
```

With no `agents`/`commands` key, everything discovered is installed. An empty list
(`agents: []`) installs none. Running `add -a ...` or `add -c ...` again *replaces* the
previous selection.

## Fetch without linking

```bash
skillset add vivainio/agent-skills --fetch
```

Clones and caches the repo and registers it with `enabled: []`, `agents: []` and
`commands: []`, linking nothing. Use it to pull a repo into the cache so you can
[search and read](searching.md) its skills later. A later `skillset update` only prompts
about skills added upstream after the fetch.

## Copy instead of symlink

```bash
skillset add vivainio/agent-skills --copy       # copy files instead of symlinking
skillset add vivainio/agent-skills --no-cache   # clone to a temp dir, copy, clean up
```

`--copy` is useful on Windows without admin privileges.

## Snapshots

```bash
skillset add vivainio/agent-skills -s zaira --snapshot
```

Copies the selected skills as-is (implies `--copy`) and pins the entry to the resolved
HEAD SHA with `snapshot: true`. `skillset update` skips snapshot entries entirely. To
refresh one, re-run `add ... --snapshot`. To convert back to live links:

```bash
skillset add vivainio/agent-skills -s zaira --unsnapshot
```

## From a local path

```bash
skillset add /path/to/skills-dir                 # all skills from a local dir
skillset add /path/to/skills-dir -s zaira        # one skill
skillset add zaira                               # look up by name in all sources
```

Local paths are registered as *editable* in the global `skillset.yaml` so `update` can
find them later. Adding by bare name searches every source; if several match you are
asked to choose.

## Trial installs

```bash
skillset add --try vivainio/agent-skills    # install on trial
skillset list                               # trial skills are tagged (trial)
skillset clean                              # remove all trial skills and their cached repos
skillset add vivainio/agent-skills          # re-add without --try to keep it
```
