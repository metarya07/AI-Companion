"""Memory agent: remember small facts about the user as key/value prefs.

Examples:
    set name Tony
    set editor = vscode
    get name
    prefs
    unset editor
"""

from __future__ import annotations

from core.registry import Skill
from core.types import ParsedCommand
from memory.prefs import PrefStore


class PrefSkill(Skill):
    name = "Preferences"
    triggers = ("set", "get", "prefs", "unset")
    help = (
        ("set <key> <value>", "Save a preference (set name Tony)"),
        ("get <key>", "Show a saved preference"),
        ("prefs", "List all preferences"),
        ("unset <key>", "Remove a preference"),
    )

    def __init__(self, store: PrefStore) -> None:
        self.store = store

    def handle(self, command: ParsedCommand) -> str:
        verb, args = command.verb, command.args.strip()

        if verb == "set":
            key, value = self._split_kv(args)
            if not key or not value:
                return "Use: set <key> <value>   e.g. set name Tony"
            self.store.set(key, value)
            return f"Saved: {key.lower()} = {value}"

        if verb == "get":
            if not args:
                return "Get what? e.g. get name"
            value = self.store.get(args)
            return value if value is not None else f"No preference set for '{args.lower()}'."

        if verb == "prefs":
            rows = self.store.all()
            if not rows:
                return "No preferences saved yet. Try: set name Tony"
            width = max(len(k) for k, _ in rows)
            return "\n".join(f"{k.ljust(width)}  {v}" for k, v in rows)

        if verb == "unset":
            if not args:
                return "Unset what? e.g. unset name"
            removed = self.store.delete(args)
            return f"Removed '{args.lower()}'." if removed else f"No preference '{args.lower()}'."

        return "I don't understand that preferences command."

    @staticmethod
    def _split_kv(args: str):
        if "=" in args:
            key, value = args.split("=", 1)
        else:
            parts = args.split(maxsplit=1)
            key = parts[0] if parts else ""
            value = parts[1] if len(parts) > 1 else ""
        return key.strip(), value.strip()
