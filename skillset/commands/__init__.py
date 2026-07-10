"""Command handlers -- dispatched from cli.py."""

from skillset.commands.add import cmd_add, cmd_init
from skillset.commands.install_skills import cmd_install_skills
from skillset.commands.list import cmd_list
from skillset.commands.remove import cmd_clean, cmd_remove
from skillset.commands.search import cmd_search
from skillset.commands.update import cmd_update

__all__ = [
    "cmd_add",
    "cmd_clean",
    "cmd_init",
    "cmd_install_skills",
    "cmd_list",
    "cmd_remove",
    "cmd_search",
    "cmd_update",
]
