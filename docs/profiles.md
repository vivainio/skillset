# Profiles

Save and switch between snapshots of your active global skills.

```bash
skillset profile          # interactive menu: switch, save or delete
skillset profile work     # switch directly to a saved profile
```

The menu uses `fzf` when installed and otherwise a numbered terminal menu. When saving,
skillset can optionally include unmanaged skills; those are moved safely into
`~/.claude/.skillset/skills/` and linked back. Switching only changes skills known to
profiles — unrelated unmanaged skills are left alone.
