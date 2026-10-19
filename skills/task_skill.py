"""Planning agent: a simple task list with optional due dates.

Examples:
    task submit lab report due friday
    todo call the bank
    tasks                 (list pending)
    tasks all             (include completed)
    done 2
    agenda                (overdue + due today)
"""

from __future__ import annotations

import datetime as _dt
from typing import Callable, Iterable, Optional, Tuple

from core.dates import parse_due
from core.registry import Skill
from core.types import ParsedCommand
from memory.tasks import Task, TaskStore


class TaskSkill(Skill):
    name = "Planner"
    triggers = ("task", "todo", "tasks", "todos", "done", "agenda")
    help = (
        ("task <text> [due <when>]", "Add a task (when: today, friday, 2026-06-20...)"),
        ("tasks", "List pending tasks ('tasks all' includes done)"),
        ("done <id>", "Mark a task complete"),
        ("agenda", "Show overdue and due-today tasks"),
    )

    def __init__(self, store: TaskStore, today: Callable[[], _dt.date] = _dt.date.today) -> None:
        self.store = store
        self._today = today

    def handle(self, command: ParsedCommand) -> str:
        verb, args = command.verb, command.args.strip()

        if verb in ("task", "todo"):
            if args.lower().startswith("add "):
                args = args[4:].strip()
            if not args:
                return "What's the task? e.g. task submit report due friday"
            text, due = self._split_due(args)
            task_id = self.store.add(text, due)
            if due:
                return f"Task #{task_id} added (due {self._humanize(due)})."
            return f"Task #{task_id} added."

        if verb in ("tasks", "todos"):
            if args.lower() == "all":
                return self._format(self.store.all(), include_done=True)
            return self._format(self.store.pending(), include_done=False)

        if verb == "done":
            if not args.isdigit():
                return "Which task? e.g. done 3."
            ok = self.store.complete(int(args))
            return (
                f"Task {args} marked done." if ok
                else f"Task {args} not found (or already done)."
            )

        if verb == "agenda":
            return self._agenda()

        return "I don't understand that task command."

    # --- helpers -------------------------------------------------------------
    def _split_due(self, args: str) -> Tuple[str, Optional[str]]:
        low = args.lower()
        idx = low.rfind(" due ")
        if idx != -1:
            spec = args[idx + 5:].strip()
            due = parse_due(spec, self._today())
            if due:
                return args[:idx].strip(), due
        return args, None

    @staticmethod
    def _humanize(iso: str) -> str:
        try:
            return _dt.date.fromisoformat(iso).strftime("%a %d %b")
        except ValueError:  # pragma: no cover - defensive
            return iso

    def _format(self, tasks: Iterable[Task], include_done: bool) -> str:
        rows = []
        for t in tasks:
            mark = "x" if t.done else " "
            due = f"  (due {self._humanize(t.due)})" if t.due else ""
            rows.append(f"{t.id}. [{mark}] {t.text}{due}")
        if rows:
            return "\n".join(rows)
        return "No tasks yet. Add one with: task buy milk" if include_done else (
            "No pending tasks. Add one with: task buy milk"
        )

    def _agenda(self) -> str:
        today = self._today().isoformat()
        due = self.store.due_until(today)
        if not due:
            return "Nothing overdue or due today. You're all caught up."
        overdue = [t for t in due if t.due and t.due < today]
        today_tasks = [t for t in due if t.due == today]
        lines = []
        if overdue:
            lines.append("Overdue:")
            lines += [f"  {t.id}. {t.text} (was due {self._humanize(t.due)})" for t in overdue]
        if today_tasks:
            lines.append("Due today:")
            lines += [f"  {t.id}. {t.text}" for t in today_tasks]
        return "\n".join(lines)
