"""Tells the time and date."""

from __future__ import annotations

from datetime import datetime
from typing import Callable

from core.registry import Skill
from core.types import ParsedCommand


class TimeSkill(Skill):
    name = "Time"
    triggers = ("time", "date", "now")
    help = (
        ("time", "Show the current time"),
        ("date", "Show today's date"),
    )

    def __init__(self, clock: Callable[[], datetime] = datetime.now) -> None:
        # The clock is injectable so tests can pin it to a fixed moment.
        self._now = clock

    def handle(self, command: ParsedCommand) -> str:
        now = self._now()
        if command.verb == "date":
            return now.strftime("Today is %A, %d %B %Y.")
        return now.strftime("Current time: %H:%M:%S")
