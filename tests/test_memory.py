"""The Database stores memories in an explicit, cwd-independent file."""

from __future__ import annotations

from memory.database import Database, Memory


def test_add_returns_sequential_ids(database):
    assert database.add("first") == 1
    assert database.add("second") == 2


def test_all_returns_rows_in_order(database):
    database.add("alpha")
    database.add("beta")
    rows = database.all()
    assert [m.text for m in rows] == ["alpha", "beta"]
    assert all(isinstance(m, Memory) for m in rows)
    assert all(m.created_at for m in rows)  # timestamp is populated


def test_add_strips_whitespace(database):
    database.add("   spaced out   ")
    assert database.all()[0].text == "spaced out"


def test_search_is_substring_and_case_insensitive(database):
    database.add("Buy milk")
    database.add("Finish OS assignment")
    hits = database.search("milk")
    assert len(hits) == 1
    assert hits[0].text == "Buy milk"
    # ASCII LIKE is case-insensitive.
    assert database.search("MILK")[0].text == "Buy milk"
    assert database.search("nothing") == []


def test_delete_reports_whether_a_row_existed(database):
    database.add("temp")
    assert database.delete(1) is True
    assert database.delete(1) is False  # already gone
    assert database.delete(999) is False


def test_clear_removes_everything_and_counts(database):
    database.add("a")
    database.add("b")
    assert database.clear() == 2
    assert database.all() == []


def test_data_persists_across_connections(db_path):
    """A second Database on the same path sees the first one's data.

    This is the regression guard for the old bug where the DB path was
    relative to the working directory and memory could silently fragment.
    """
    first = Database(db_path)
    first.add("persisted")

    second = Database(db_path)
    assert [m.text for m in second.all()] == ["persisted"]


def test_parent_directories_are_created(tmp_path):
    nested = tmp_path / "a" / "b" / "c" / "jarvis.db"
    db = Database(nested)
    db.add("ok")
    assert nested.exists()
    assert db.all()[0].text == "ok"
