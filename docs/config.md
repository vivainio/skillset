# skillset.yaml

Manage skills declaratively in a `skillset.yaml`: globally at `~/.claude/skillset.yaml`
or per project at the repo root.

```bash
skillset init           # create skillset.yaml at the git root
skillset init -g        # create ~/.claude/skillset.yaml
```

Each entry under `skills:` is keyed by `owner/repo`:

```yaml
# names installed outside skillset; update never replaces or removes them
unmanaged: [zenkins]

skills:
  # all skills from the repo
  vivainio/agent-skills:
    enabled: ["*"]

  # selective: enable zaira, explicitly skip another
  vivainio/agent-skills:
    enabled: [zaira]
    disabled: [some-other]

  # glob patterns: everything with a prefix, minus one
  vivainio/agent-skills:
    enabled: ["doc-*"]
    disabled: [doc-draft]

  # skills from a subdirectory
  vivainio/agent-skills:
    path: extra-skills
    enabled: ["*"]

  # copy instead of symlinking
  vivainio/agent-skills:
    copy: true
    enabled: ["*"]

  # editable: a local checkout instead of the cache
  vivainio/agent-skills:
    path: extra-skills
    editable: true
    source: ~/repos/agent-skills
    enabled: ["*"]

# arbitrary cross-repo symlinks
links:
  specs: ../project-docs/specs
```

**Editable** entries point at a local checkout: set `editable: true` and `source`, and
use `path` to select a subdirectory.

`links:` creates symlinks for cross-repo paths and warns if a target is not in
`.gitignore`.

Any entry containing `*`, `?`, `[` or `%` is an fnmatch glob against skill names, with
`%` as an alias for `*`.
