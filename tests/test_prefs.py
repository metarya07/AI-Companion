"""PrefStore persistence and PrefSkill behaviour."""

from __future__ import annotations

from core.types import ParsedCommand
from memory.prefs import PrefStore
from skills.prefs_skill import PrefSkill


def _cmd(raw: str) -> ParsedCommand:
    parts = raw.split(maxsplit=1)
    verb = parts[0].lower() if parts else ""
    args = parts[1] if len(parts) > 1 else ""
    return ParsedCommand(raw=raw, verb=verb, args=args)


# --- store ---------------------------------------------------------------
def test_store_set_get_overwrite(db_path):
    store = PrefStore(db_path)
    store.set("name", "Tony")
    assert store.get("name") == "Tony"
    store.set("name", "Steve")  # overwrite
    assert store.get("name") == "Steve"
    assert store.get("missing") is None


def test_store_all_and_delete(db_path):
    store = PrefStore(db_path)
    store.set("a", "1")
    store.set("b", "2")
    assert dict(store.all()) == {"a": "1", "b": "2"}
    assert store.delete("a") is True
    assert store.delete("a") is False


# --- skill ---------------------------------------------------------------
def test_skill_set_and_get(db_path):
    skill = PrefSkill(PrefStore(db_path))
    assert skill.handle(_cmd("set name Tony")) == "Saved: name = Tony"
    assert skill.handle(_cmd("get name")) == "Tony"


def test_skill_set_with_equals(db_path):
    skill = PrefSkill(PrefStore(db_path))
    skill.handle(_cmd("set editor = vscode"))
    assert skill.handle(_cmd("get editor")) == "vscode"


def test_skill_list_and_unset(db_path):
    skill = PrefSkill(PrefStore(db_path))
    skill.handle(_cmd("set city Delhi"))
    assert "city" in skill.handle(_cmd("prefs"))
    assert skill.handle(_cmd("unset city")) == "Removed 'city'."
    assert "No preferences" in skill.handle(_cmd("prefs"))


def test_skill_missing_key(db_path):
    skill = PrefSkill(PrefStore(db_path))
    assert "No preference set for 'nope'." == skill.handle(_cmd("get nope"))
