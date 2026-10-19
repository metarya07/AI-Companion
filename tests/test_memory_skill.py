"""MemorySkill: remember / recall / search / forget behaviour."""

from __future__ import annotations

from skills.memory_skill import MemorySkill
from core.types import ParsedCommand


def _cmd(raw: str) -> ParsedCommand:
    parts = raw.split(maxsplit=1)
    verb = parts[0].lower() if parts else ""
    args = parts[1] if len(parts) > 1 else ""
    return ParsedCommand(raw=raw, verb=verb, args=args)


def test_remember_saves_and_reports_id(database):
    skill = MemorySkill(database)
    assert skill.handle(_cmd("remember buy milk")) == "Memory saved (#1)."
    assert database.all()[0].text == "buy milk"


def test_remember_without_text_prompts(database):
    skill = MemorySkill(database)
    assert "remember" in skill.handle(_cmd("remember")).lower()
    assert database.all() == []


def test_recall_lists_memories(database):
    skill = MemorySkill(database)
    skill.handle(_cmd("remember one"))
    skill.handle(_cmd("remember two"))
    out = skill.handle(_cmd("recall"))
    assert out == "1. one\n2. two"


def test_recall_when_empty(database):
    skill = MemorySkill(database)
    assert skill.handle(_cmd("recall")) == "No memories yet."


def test_search_filters(database):
    skill = MemorySkill(database)
    skill.handle(_cmd("remember buy milk"))
    skill.handle(_cmd("remember call mum"))
    assert skill.handle(_cmd("search milk")) == "1. buy milk"
    assert "No memories match" in skill.handle(_cmd("search zzz"))


def test_forget_validates_id(database):
    skill = MemorySkill(database)
    assert "valid memory ID" in skill.handle(_cmd("forget abc"))


def test_forget_existing_and_missing(database):
    skill = MemorySkill(database)
    skill.handle(_cmd("remember temp"))
    assert skill.handle(_cmd("forget 1")) == "Memory 1 deleted."
    assert skill.handle(_cmd("forget 1")) == "Memory 1 not found."
