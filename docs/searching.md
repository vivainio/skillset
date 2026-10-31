# Finding and reading skills

Both commands are local and offline: they look at every repo already in the cache
(`skillset add ... --fetch` is a good way to get one there), editable sources registered
in the global `skillset.yaml`, and unmanaged skills.

## search

```bash
skillset search jira            # names/descriptions matching "jira"
skillset search jenkins build   # all terms must match (AND)
skillset search jira-%          # glob: name starting with "jira-"
skillset search %config%        # glob: "config" anywhere in name or description
```

A term containing a wildcard is matched as a glob against the skill name and the full
name+description text; plain terms are substring matches.

## get

```bash
skillset get zaira
```

Prints a skill's `SKILL.md` **without installing it**, so you can use a skill without
linking it into `~/.claude/skills/` and paying for it in every session's context.

The output has:

1. a header with the skill name, its source (`owner/repo`) and directory,
2. the `SKILL.md` content (relative paths in it are relative to that directory),
3. a `# Resources` list of paths to every other file in the skill (hidden
   entries skipped, capped at 200).

```text
# Skill: zaira  [owner/repo]
# Directory: ~/.cache/skillset/repos/owner/repo/zaira
# Relative paths in the SKILL.md below are relative to that directory.

---
name: zaira
description: Access Jira tickets offline
---
...

# Resources
~/.cache/skillset/repos/owner/repo/zaira/references/api.md
~/.cache/skillset/repos/owner/repo/zaira/scripts/fetch.sh
```

`get` takes the same terms and wildcards as `search`. If several skills match, an exact
name match wins; otherwise it lists the candidates on stderr and exits 1. No match also
exits 1. Errors go to stderr so stdout stays clean for an agent to read.

!!! note
    `get` only reads sources that are already cached or registered. It does not clone
    repos you have not added.
