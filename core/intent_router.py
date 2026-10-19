"""Decides which intent a parsed command maps to.

The router no longer carries a hand-written ``if/elif`` ladder of every
command. It asks the registry which verbs are known and otherwise sends
the input to the AI fallback (the ``"chat"`` intent). A few "meta"
commands about the assistant itself (help, version, exit) are handled
here so they always behave consistently.
"""

from __future__ import annotations

from core.registry import SkillRegistry
from core.types import ParsedCommand

EXIT_VERBS = {"exit", "quit", "bye"}
META_VERBS = {"help", "version"}


class IntentRouter:
    def __init__(self, registry: SkillRegistry) -> None:
        self.registry = registry

    def route(self, command: ParsedCommand) -> str:
        verb = command.verb
        if not verb:
            return "empty"
        if verb in EXIT_VERBS:
            return "exit"
        if verb in META_VERBS:
            return verb
        if verb in self.registry.verbs():
            return verb
        # Unknown verb -> let the AI assistant try to help.
        return "chat"
