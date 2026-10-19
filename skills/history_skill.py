"""Memory agent: review the persistent conversation log.

Examples:
    history          (last 10 turns)
    history 25
    history clear
"""

from __future__ import annotations

from core.registry import Skill
from core.types import ParsedCommand
from memory.history import HistoryStore


class HistorySkill(Skill):
    name = "History"
    triggers = ("history",)
    help = (
        ("history [n]", "Show the last n conversation turns (default 10)"),
        ("history clear", "Erase the conversation history"),
    )

    def __init__(self, store: HistoryStore) -> None:
        self.store = store

    def handle(self, command: ParsedCommand) -> str:
        args = command.args.strip().lower()

        if args == "clear":
            removed = self.store.clear()
            return f"Conversation history cleared ({removed} turns removed)."

        limit = int(args) if args.isdigit() else 10
        turns = self.store.recent(limit)
        if not turns:
            return "No conversation history yet."
        blocks = [f"you>    {t.user_text}\njarvis> {t.jarvis_text}" for t in turns]
        return "\n\n".join(blocks)
