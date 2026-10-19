"""ScheduleSkill: register, list, and remove scheduled commands."""

from __future__ import annotations

from core.types import ParsedCommand
from memory.schedules import ScheduleStore
from skills.schedule_skill import ScheduleSkill


def _cmd(raw: str) -> ParsedCommand:
    parts = raw.split(maxsplit=1)
    verb = parts[0].lower() if parts else ""
    args = parts[1] if len(parts) > 1 else ""
    return ParsedCommand(raw=raw, verb=verb, args=args)


def test_schedule_add_and_split(db_path):
    store = ScheduleStore(db_path)
    skill = ScheduleSkill(store)
    out = skill.handle(_cmd("schedule clean ~/Downloads every sunday at 09:00"))
    assert "Scheduled #1" in out
    saved = store.all()[0]
    assert saved.command == "clean ~/Downloads"
    assert saved.spec == "every sunday at 09:00"


def test_schedule_rejects_bad_spec(db_path):
    skill = ScheduleSkill(ScheduleStore(db_path))
    out = skill.handle(_cmd("schedule do thing every fortnight"))
    assert "couldn't understand" in out


def test_schedule_missing_spec(db_path):
    skill = ScheduleSkill(ScheduleStore(db_path))
    out = skill.handle(_cmd("schedule justacommand"))
    assert out.startswith("Use:")


def test_schedules_list(db_path):
    store = ScheduleStore(db_path)
    skill = ScheduleSkill(store)
    assert "No schedules yet" in skill.handle(_cmd("schedules"))
    skill.handle(_cmd("schedule backup ~/notes every day at 22:00"))
    listing = skill.handle(_cmd("schedules"))
    assert "backup ~/notes" in listing and "never run" in listing


def test_unschedule(db_path):
    store = ScheduleStore(db_path)
    skill = ScheduleSkill(store)
    skill.handle(_cmd("schedule backup ~/notes every day"))
    assert "removed" in skill.handle(_cmd("unschedule 1")).lower()
    assert "not found" in skill.handle(_cmd("unschedule 1"))
    assert "Which schedule" in skill.handle(_cmd("unschedule abc"))
