"""Automation agent: schedule JARVIS commands to run periodically.

Examples:
    schedule backup ~/notes every day at 22:00
    schedule clean ~/Downloads every sunday at 09:00
    schedules
    unschedule 1

The schedules are stored; an OS scheduler (cron / Task Scheduler) should
run ``jarvis --run-due`` regularly to execute whatever is due.
"""

from __future__ import annotations

from core.registry import Skill
from core.schedule import parse_spec
from core.types import ParsedCommand
from memory.schedules import ScheduleStore

_SUPPORTED = (
    "Supported recurrences: 'every hour', 'every day [at HH:MM]', "
    "'every <weekday> [at HH:MM]'."
)


class ScheduleSkill(Skill):
    name = "Automation"
    triggers = ("schedule", "schedules", "unschedule")
    help = (
        ("schedule <command> every <when>", "Run a command on a recurring schedule"),
        ("schedules", "List scheduled commands"),
        ("unschedule <id>", "Remove a schedule"),
    )

    def __init__(self, store: ScheduleStore) -> None:
        self.store = store

    def handle(self, command: ParsedCommand) -> str:
        verb, args = command.verb, command.args.strip()

        if verb == "schedules":
            return self._list()

        if verb == "unschedule":
            if not args.isdigit():
                return "Which schedule? e.g. unschedule 1"
            return (
                f"Schedule {args} removed." if self.store.delete(int(args))
                else f"Schedule {args} not found."
            )

        # verb == "schedule" -> register a new one.
        cmd_text, spec_text = self._split(args)
        if not cmd_text or not spec_text:
            return (
                "Use: schedule <command> every <when>\n"
                "e.g. schedule clean ~/Downloads every sunday at 09:00\n" + _SUPPORTED
            )
        if parse_spec(spec_text) is None:
            return f"I couldn't understand '{spec_text}'.\n{_SUPPORTED}"
        schedule_id = self.store.add(cmd_text, spec_text)
        return (
            f"Scheduled #{schedule_id}: '{cmd_text}' — {spec_text}.\n"
            "It runs when 'jarvis --run-due' is invoked (e.g. by cron)."
        )

    @staticmethod
    def _split(args: str):
        """Split "<command> every <when>" on the last ' every '."""
        low = args.lower()
        idx = low.rfind(" every ")
        if idx == -1:
            if low.startswith("every "):
                return "", args.strip()
            return args.strip(), ""
        command = args[:idx].strip()
        spec = args[idx + 1:].strip()  # keep the "every ..." part
        return command, spec

    def _list(self) -> str:
        rows = self.store.all()
        if not rows:
            return (
                "No schedules yet. Add one with:\n"
                "  schedule clean ~/Downloads every sunday at 09:00"
            )
        lines = []
        for s in rows:
            last = f"last run {s.last_run}" if s.last_run else "never run"
            lines.append(f"{s.id}. {s.command} — {s.spec}  ({last})")
        return "\n".join(lines)
