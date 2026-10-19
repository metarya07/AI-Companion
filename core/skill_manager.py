"""Executes a routed command and produces the response text.

Improvements over the original manager:

* It dispatches through the registry instead of a giant ``if/elif`` block,
  so it never needs editing when a skill is added.
* Help text is generated from the registered skills, so it can no longer
  drift out of sync with the commands that actually exist.
* Every skill call is wrapped so that one misbehaving skill returns a
  friendly message instead of crashing the whole assistant.
"""

from __future__ import annotations

import logging

from core.registry import Skill, SkillRegistry
from core.types import ParsedCommand

log = logging.getLogger("jarvis.skill_manager")

_GENERAL_HELP = (
    ("help", "Show this help"),
    ("version", "Show the JARVIS version"),
    ("exit", "Quit JARVIS"),
)


class SkillManager:
    def __init__(self, registry: SkillRegistry, fallback: Skill, version: str) -> None:
        self.registry = registry
        self.fallback = fallback
        self.version = version

    def execute(self, intent: str, command: ParsedCommand) -> str:
        if intent == "empty":
            return ""
        if intent == "exit":
            return "Goodbye."
        if intent == "version":
            return f"JARVIS {self.version}"
        if intent == "help":
            return self.help_text()

        skill = self.registry.get(intent) or self.fallback
        try:
            return skill.handle(command)
        except Exception as exc:  # noqa: BLE001 - we want to catch everything here
            log.exception("Skill %r failed on input %r", skill.name, command.raw)
            return (
                f"Sorry, something went wrong while handling that "
                f"({type(exc).__name__}). The rest of JARVIS is still fine."
            )

    def help_text(self) -> str:
        sections = [("General", list(_GENERAL_HELP))]
        for skill in self.registry.skills():
            if skill.help:
                sections.append((skill.name, list(skill.help)))

        all_commands = [entry for _, entries in sections for entry in entries]
        width = max((len(cmd) for cmd, _ in all_commands), default=0)

        lines = ["JARVIS - available commands", ""]
        for title, entries in sections:
            lines.append(f"{title}:")
            for cmd, desc in entries:
                lines.append(f"  {cmd.ljust(width)}  {desc}")
            lines.append("")
        lines.append("Anything that isn't a command is sent to the AI assistant.")
        return "\n".join(lines)
