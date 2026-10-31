# Removing skills

```bash
skillset remove zaira          # remove from the detected scope
skillset remove zaira -g       # remove from global skills
skillset remove ai-%           # glob; % is a shell-safe wildcard
skillset remove -i             # pick skills with fzf
```

## A whole repo

```bash
skillset remove JuliusBrussee/caveman
```

A name containing `/` is treated as `owner/repo`: it unlinks every skill and command
sourced from it, drops its `skillset.yaml` entry and deletes the cached clone.

## Everything

```bash
skillset remove --all      # detected scope
skillset remove --all -g   # global skillset.yaml
```

Equivalent to `remove owner/repo` for every entry, then wipes the whole repo cache.

!!! warning
    The cache is shared machine-wide, not scoped to local or global, so `--all` also
    deletes cached clones belonging to other projects and untracked trial repos.
