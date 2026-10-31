# How it works

- Skills are symlinked (Linux/macOS) or junctioned (Windows) from cached repos.
- Repo sources live in `~/.local/share/skillset/repos/` on Linux,
  `~/Library/Application Support/skillset/repos/` on macOS and
  `%LOCALAPPDATA%\skillset\repos` on Windows. Existing clones in the legacy
  `~/.cache/skillset/repos/` remain supported.
- Global scope honors `CLAUDE_CONFIG_DIR`: when set, skillset reads and writes
  `skills/`, `commands/`, `agents/` and `skillset.yaml` under that directory instead of
  `~/.claude/`.
