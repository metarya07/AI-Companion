"""TaskStore persistence and TaskSkill behaviour."""

from __future__ import annotations

import datetime as _dt

from core.types import ParsedCommand
from memory.tasks import TaskStore
from skills.task_skill import TaskSkill

TODAY = _dt.date(2026, 6, 14)


def _cmd(raw: str) -> ParsedCommand:
    parts = raw.split(maxsplit=1)
    verb = parts[0].lower() if parts else ""
    args = parts[1] if len(parts) > 1 else ""
    return ParsedCommand(raw=raw, verb=verb, args=args)


# --- store ---------------------------------------------------------------
def test_store_add_and_pending(db_path):
    store = TaskStore(db_path)
    store.add("a")
    store.add("b")
    assert [t.text for t in store.pending()] == ["a", "b"]


def test_store_orders_dated_before_undated(db_path):
    store = TaskStore(db_path)
    store.add("a")                       # no due
    store.add("b", "2026-06-20")
    store.add("c", "2026-06-15")
    assert [t.text for t in store.all()] == ["c", "b", "a"]


def test_store_complete_and_due_until(db_path):
    store = TaskStore(db_path)
    store.add("soon", "2026-06-15")
    store.add("later", "2026-06-30")
    assert [t.text for t in store.due_until("2026-06-16")] == ["soon"]
    assert store.complete(1) is True
    assert store.pending()[0].text == "later"


# --- skill ---------------------------------------------------------------
def test_skill_add_plain(db_path):
    skill = TaskSkill(TaskStore(db_path), today=lambda: TODAY)
    assert skill.handle(_cmd("task submit report")) == "Task #1 added."


def test_skill_add_with_due(db_path):
    skill = TaskSkill(TaskStore(db_path), today=lambda: TODAY)
    out = skill.handle(_cmd("task call bank due tomorrow"))
    assert out == "Task #1 added (due Mon 15 Jun)."


def test_skill_list_and_complete(db_path):
    skill = TaskSkill(TaskStore(db_path), today=lambda: TODAY)
    skill.handle(_cmd("task one"))
    skill.handle(_cmd("task two"))
    listing = skill.handle(_cmd("tasks"))
    assert "1. [ ] one" in listing and "2. [ ] two" in listing

    assert skill.handle(_cmd("done 1")) == "Task 1 marked done."
    assert "one" not in skill.handle(_cmd("tasks"))
    assert "[x] one" in skill.handle(_cmd("tasks all"))


def test_skill_done_validation(db_path):
    skill = TaskSkill(TaskStore(db_path), today=lambda: TODAY)
    assert "Which task" in skill.handle(_cmd("done abc"))
    assert "not found" in skill.handle(_cmd("done 99"))


def test_skill_agenda(db_path):
    store = TaskStore(db_path)
    store.add("late thing", "2026-06-10")   # overdue
    store.add("today thing", "2026-06-14")  # due today
    store.add("future thing", "2026-06-20")
    skill = TaskSkill(store, today=lambda: TODAY)
    out = skill.handle(_cmd("agenda"))
    assert "Overdue:" in out and "late thing" in out
    assert "Due today:" in out and "today thing" in out
    assert "future thing" not in out


def test_skill_agenda_empty(db_path):
    skill = TaskSkill(TaskStore(db_path), today=lambda: TODAY)
    assert "caught up" in skill.handle(_cmd("agenda"))
