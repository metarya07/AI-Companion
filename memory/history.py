"""Persistent conversation log for the memory agent.

Each turn (what the user said and how JARVIS replied) is appended here so
the user can review past sessions. The AI skill keeps its own in-session
context separately; this is the durable record.
"""

from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
from typing import List, Union

from memory.store import connect, ensure_parent


@dataclass(frozen=True)
class Turn:
    id: int
    user_text: str
    jarvis_text: str
    ts: str


_SCHEMA = """
CREATE TABLE IF NOT EXISTS history (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_text   TEXT NOT NULL,
    jarvis_text TEXT NOT NULL,
    ts          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""


class HistoryStore:
    def __init__(self, path: Union[str, Path]) -> None:
        self.path = str(path)
        ensure_parent(self.path)
        with closing(connect(self.path)) as conn:
            conn.execute(_SCHEMA)
            conn.commit()

    def add(self, user_text: str, jarvis_text: str) -> int:
        with closing(connect(self.path)) as conn:
            cur = conn.execute(
                "INSERT INTO history (user_text, jarvis_text) VALUES (?, ?)",
                (user_text, jarvis_text),
            )
            conn.commit()
            return int(cur.lastrowid)

    def recent(self, limit: int = 10) -> List[Turn]:
        with closing(connect(self.path)) as conn:
            rows = conn.execute(
                "SELECT * FROM (SELECT * FROM history ORDER BY id DESC LIMIT ?) "
                "ORDER BY id",
                (max(1, limit),),
            ).fetchall()
        return [Turn(r["id"], r["user_text"], r["jarvis_text"], r["ts"]) for r in rows]

    def count(self) -> int:
        with closing(connect(self.path)) as conn:
            return int(conn.execute("SELECT COUNT(*) AS n FROM history").fetchone()["n"])

    def clear(self) -> int:
        with closing(connect(self.path)) as conn:
            cur = conn.execute("DELETE FROM history")
            conn.commit()
            return cur.rowcount
