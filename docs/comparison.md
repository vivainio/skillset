# Comparison with `npx skills`

Vercel's [`skills`](https://github.com/vercel-labs/skills) CLI is a cross-agent package
manager with a central registry at [skills.sh](https://skills.sh). Both manage
`SKILL.md`-based skills from GitHub repos, but differ in scope.

|                 | **skillset**                              | **Vercel `npx skills`**               |
| --------------- | ----------------------------------------- | ------------------------------------- |
| Target agents   | Claude Code                               | 40+ (Claude, Cursor, Codex, Copilot…) |
| Slash commands  | Links `/commands` from repos              | No                                    |
| Skill discovery | Local search over cached repos (`search`) | Central registry (89K+ skills)        |
| Install method  | `pip` / `uv tool install` / `uvx`         | `npx`                                 |
| Scope default   | Project if available, Global otherwise    | Project                               |

skillset is a Claude Code power-user tool; Vercel's CLI is a cross-agent marketplace.
They are complementary — discover via the registry, install and manage via skillset.
