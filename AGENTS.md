# skillset

CLI tool for managing Claude Code AI skills across projects. Installs, links,
and syncs SKILL.md-based skills from GitHub repos or local directories into
`~/.claude/skills/` (global) or `.claude/skills/` (project-local).

## Codebase structure

```
skillset/
  cli.py              Typer CLI entrypoint, command definitions
  commands/            Command handlers package
    __init__.py        Re-exports all cmd_* for cli.py
    _resolve.py        Source resolution helpers for add
    _templates.py      skillset.yaml templates
    add.py             cmd_add, cmd_init
    list.py            cmd_list
    remove.py          cmd_remove, cmd_clean
    update.py          cmd_update
  discovery.py         Find SKILL.md files and commands in repos
  linking.py           Symlink/junction creation, managed copies
  manifest.py          Install manifest (JSON) load/save/query
  paths.py             Path resolution, skillset.yaml updates
  repo.py              Git clone/pull, GitHub URL parsing
  ui.py                Interactive prompts, fzf integration
tests/                 Mirrors skillset/ structure per module
```

## Code rules

- Max **mccabe complexity 10** (enforced by ruff C901)

## Testing

Use the `/unit-test` skill when writing tests -- it explains test structure,
conventions, and fixtures. Integration tests, ruff, and line-length checks
are special cases not covered by `/unit-test`.

## Running checks

```bash
bash test.sh                                  # all checks at once
ruff check skillset                           # lint + complexity
ruff format --check skillset                  # format
pytest tests/ --ignore=tests/integration -q   # unit tests
pytest tests/integration -q                   # integration tests
```
