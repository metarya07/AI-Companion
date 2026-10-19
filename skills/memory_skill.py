"""Remembers, recalls, searches and forgets notes."""

from __future__ import annotations

from typing import Iterable

from core.registry import Skill
from core.types import ParsedCommand
from memory.database import Database, Memory


class MemorySkill(Skill):
    name = "Memory"
    triggers = ("remember", "recall", "memories", "search", "forget")
    help = (
        ("remember <text>", "Save a note to long-term memory"),
        ("recall", "List everything you've remembered"),
        ("search <text>", "Find saved notes containing some text"),
        ("forget <id>", "Delete the note with that id"),
    )

    def __init__(self, db: Database) -> None:
        self.db = db

    def handle(self, command: ParsedCommand) -> str:
        verb, args = command.verb, command.args

        if verb == "remember":
            if not args:
                return "What should I remember? Try: remember buy milk"
            memory_id = self.db.add(args)
            return f"Memory saved (#{memory_id})."

        if verb in ("recall", "memories"):
            return self._format(self.db.all(), empty="No memories yet.")

        if verb == "search":
            if not args:
                return "Search for what? Try: search milk"
            return self._format(
                self.db.search(args), empty=f"No memories match '{args}'."
            )

        if verb == "forget":
            if not args.isdigit():
                return "Please provide a valid memory ID, e.g. forget 3."
            deleted = self.db.delete(int(args))
            return f"Memory {args} deleted." if deleted else f"Memory {args} not found."

        return "I don't understand that memory command."

    @staticmethod
    def _format(memories: Iterable[Memory], empty: str) -> str:
        rows = [f"{m.id}. {m.text}" for m in memories]
        return "\n".join(rows) if rows else empty
