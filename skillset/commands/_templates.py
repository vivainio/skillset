"""Shared templates for command handlers."""

GLOBAL_SKILLSET_TEMPLATE = """\
# Global skillset configuration (~/.claude/skillset.yaml)
# Skills are installed to ~/.claude/skills/
#
# Each entry under "skills:" is keyed by "owner/repo":
#
# skills:
#   owner/repo:
#     enabled: ["*"]                     # link every skill in the repo
#
#   owner/repo:
#     enabled: [skill-a, skill-b]        # link only these
#     disabled: [skill-c]                # explicitly skip (update won't re-prompt)
#
#   owner/repo:
#     path: subdir                       # skills live in a subdirectory
#     editable: true                     # source is a local checkout
#     source: ~/code/my-skills
#     enabled: ["*"]
#
# Glob patterns ("doc-*", "t?st", etc.) are expanded against available skills.
# Run 'skillset update' to install/update skills.

skills: {}
"""

LOCAL_SKILLSET_TEMPLATE = """\
# Project skillset configuration (skillset.yaml)
# Skills are installed to .claude/skills/
#
# Each entry under "skills:" is keyed by "owner/repo":
#
# skills:
#   owner/repo:
#     enabled: ["*"]                     # link every skill in the repo
#
#   owner/repo:
#     enabled: [skill-a, skill-b]        # link only these
#     disabled: [skill-c]                # explicitly skip (update won't re-prompt)
#
#   owner/repo:
#     path: subdir                       # skills live in a subdirectory
#
# Glob patterns ("doc-*", "t?st", etc.) are expanded against available skills.
# Run 'skillset update' to install skills.

skills: {}
"""
