"""Persistent memory storage backed by SQLite.

Changes from the original module-of-functions version:

* It is a small ``Database`` class that takes an explicit path, so the
  database location is no longer tied to the current working directory
  (running JARVIS from a different folder used to silently create a
  second, empty ``jarvis.db``).
* Parent directories are created automatically.
* Queries still use parameter binding (so they are injection-safe) and
  now return typed :class:`Memory` rows including timestamps.
* Adds ``search`` and ``clear`` to support richer memory commands.
"""

from __future__ import annotations

import sqlite3
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
from typing import List, Union

from memory.store import connect, ensure_parent


@dataclass(frozen=True)
class Memory:
    id: int
    text: str
    created_at: str


_SCHEMA = """
CREATE TABLE IF NOT EXISTS memories (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    memory_text TEXT NOT NULL,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""


class Database:
    def __init__(self, path: Union[str, Path]) -> None:
        self.path = str(path)
        ensure_parent(self.path)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        return connect(self.path)

    def _init_schema(self) -> None:
        with closing(self._connect()) as conn:
            conn.execute(_SCHEMA)
            conn.commit()

    def add(self, text: str) -> int:
        text = text.strip()
        with closing(self._connect()) as conn:
            cursor = conn.execute(
                "INSERT INTO memories (memory_text) VALUES (?)", (text,)
            )
            conn.commit()
            return int(cursor.lastrowid)

    def all(self) -> List[Memory]:
        with closing(self._connect()) as conn:
            rows = conn.execute(
                "SELECT id, memory_text, created_at FROM memories ORDER BY id"
            ).fetchall()
        return [Memory(r["id"], r["memory_text"], r["created_at"]) for r in rows]

    def search(self, query: str) -> List[Memory]:
        like = f"%{query.strip()}%"
        with closing(self._connect()) as conn:
            rows = conn.execute(
                "SELECT id, memory_text, created_at FROM memories "
                "WHERE memory_text LIKE ? ORDER BY id",
                (like,),
            ).fetchall()
        return [Memory(r["id"], r["memory_text"], r["created_at"]) for r in rows]

    def delete(self, memory_id: int) -> bool:
        with closing(self._connect()) as conn:
            cursor = conn.execute(
                "DELETE FROM memories WHERE id = ?", (memory_id,)
            )
            conn.commit()
            return cursor.rowcount > 0

    def clear(self) -> int:
        with closing(self._connect()) as conn:
            cursor = conn.execute("DELETE FROM memories")
            conn.commit()
            return cursor.rowcount
