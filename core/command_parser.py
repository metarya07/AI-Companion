"""Turns a raw input line into a structured :class:`ParsedCommand`."""

from __future__ import annotations

from core.types import ParsedCommand


class CommandParser:
    """Splits input into a verb and arguments.

    This stays deliberately small: the old version only did ``.strip()``
    and returned a string, which forced every downstream consumer to do
    its own slicing (``command[len("remember "):]`` and friends). Doing
    the split once, here, removes that duplicated, error-prone logic.
    """

    def parse(self, user_input: str) -> ParsedCommand:
        raw = (user_input or "").strip()
        if not raw:
            return ParsedCommand(raw="", verb="", args="")

        parts = raw.split(maxsplit=1)
        verb = parts[0].lower()
        args = parts[1].strip() if len(parts) > 1 else ""
        return ParsedCommand(raw=raw, verb=verb, args=args)
