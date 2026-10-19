"""Conversation history: store, skill, and the Brain recorder."""

from __future__ import annotations

from core.brain import Brain
from core.types import ParsedCommand
from memory.history import HistoryStore
from skills.history_skill import HistorySkill


def _cmd(raw: str) -> ParsedCommand:
    parts = raw.split(maxsplit=1)
    verb = parts[0].lower() if parts else ""
    args = parts[1] if len(parts) > 1 else ""
    return ParsedCommand(raw=raw, verb=verb, args=args)


# --- store ---------------------------------------------------------------
def test_store_recent_is_chronological(db_path):
    store = HistoryStore(db_path)
    store.add("first", "r1")
    store.add("second", "r2")
    store.add("third", "r3")
    recent = store.recent(2)
    assert [t.user_text for t in recent] == ["second", "third"]
    assert store.count() == 3


def test_store_clear(db_path):
    store = HistoryStore(db_path)
    store.add("x", "y")
    assert store.clear() == 1
    assert store.count() == 0


# --- skill ---------------------------------------------------------------
def test_skill_empty(db_path):
    skill = HistorySkill(HistoryStore(db_path))
    assert skill.handle(_cmd("history")) == "No conversation history yet."


def test_skill_shows_turns(db_path):
    store = HistoryStore(db_path)
    store.add("hello", "hi there")
    out = HistorySkill(store).handle(_cmd("history"))
    assert "you>" in out and "hello" in out
    assert "jarvis>" in out and "hi there" in out


def test_skill_clear(db_path):
    store = HistoryStore(db_path)
    store.add("a", "b")
    assert "cleared" in HistorySkill(store).handle(_cmd("history clear"))
    assert store.count() == 0


# --- recorder integration ------------------------------------------------
def test_brain_records_turns(settings):
    brain = Brain.create(settings)
    brain.process("time")
    brain.process("")  # empty input should NOT be recorded
    turns = HistoryStore(settings.db_path).recent(10)
    user_texts = [t.user_text for t in turns]
    assert "time" in user_texts
    assert "" not in user_texts
