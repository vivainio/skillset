# Finding and reading skills

Both commands are local and offline: they look at every repo already in the cache
(`skillset fetch ...` is a good way to get one there), editable sources registered
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

Running `get` is treated as a request to *use* the skill: the output opens with a note
telling the agent it was loaded on demand and to follow it as if it were an active skill.

The output has:

1. a header with the skill name, its source (`owner/repo`) and directory,
2. the `SKILL.md` content (relative paths in it are relative to that directory),
3. a `# Resources` list of paths to every other file in the skill (hidden
   entries skipped, capped at 200).

```text
# Skill: zaira  [owner/repo]
# Loaded on demand (not installed). Running `skillset get` means the user wants
# this skill applied: follow the instructions below as if it were an active skill.
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

### Fetching a repo on demand

```bash
skillset get owner/repo zaira
```

Put `owner/repo` before the skill name to read a skill from a repo you have not
fetched. The search is limited to that repo. If it is already in the cache it is used
as is (no network); otherwise it is cloned, and recorded as a **trial repo**, exactly
like `skillset add --try`:

- `skillset clean` removes it again,
- `skillset fetch owner/repo` keeps it in the cache; `skillset add owner/repo -s zaira` keeps it and installs the skill.

A repo that was already cached is never marked as trial, so `clean` cannot delete a
clone you meant to keep. Without the `owner/repo` prefix, `get` only reads sources that
are already cached or registered.
