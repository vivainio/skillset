# Updating

`update` applies the config: it processes `links:`, pulls each repo, links skills in
`enabled` and removes those in `disabled`.

New skills in a repo that are in neither list are handled by scope:

- **Local `skillset.yaml`** — only reported. The file is a declaration and is never
  amended without `-y`/`-n`.
- **Global config** — an interactive add / ignore / select prompt.

Snapshot entries are skipped entirely.

```bash
skillset update                              # local skillset.yaml if found, else global
skillset update -g                           # global ~/.claude/skillset.yaml
skillset update --file path/to/skillset.yaml # a specific file
skillset update -y                           # accept all new skills without prompting
skillset update -n                           # ignore all new skills without prompting
skillset update --repair                     # repair editable sources; offer to remove old clones
skillset update --repair -y                  # repair and remove redundant clones unprompted
```
