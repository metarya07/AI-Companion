"""Task storage for the planning agent (SQLite, same DB file as memories)."""

from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Union

from memory.store import connect, ensure_parent


@dataclass(frozen=True)
class Task:
    id: int
    text: str
    due: Optional[str]  # ISO date "YYYY-MM-DD" or None
    done: bool
    created_at: str


_SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    text       TEXT NOT NULL,
    due        TEXT,
    done       INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""


def _row(r) -> Task:
    return Task(r["id"], r["text"], r["due"], bool(r["done"]), r["created_at"])


class TaskStore:
    def __init__(self, path: Union[str, Path]) -> None:
        self.path = str(path)
        ensure_parent(self.path)
        with closing(connect(self.path)) as conn:
            conn.execute(_SCHEMA)
            conn.commit()

    def add(self, text: str, due: Optional[str] = None) -> int:
        with closing(connect(self.path)) as conn:
            cur = conn.execute(
                "INSERT INTO tasks (text, due) VALUES (?, ?)", (text.strip(), due)
            )
            conn.commit()
            return int(cur.lastrowid)

    def all(self, include_done: bool = True) -> List[Task]:
        sql = "SELECT * FROM tasks"
        if not include_done:
            sql += " WHERE done = 0"
        sql += " ORDER BY (due IS NULL), due, id"
        with closing(connect(self.path)) as conn:
            return [_row(r) for r in conn.execute(sql).fetchall()]

    def pending(self) -> List[Task]:
        return self.all(include_done=False)

    def due_until(self, date_str: str) -> List[Task]:
        """Pending tasks with a due date on or before ``date_str``."""
        with closing(connect(self.path)) as conn:
            rows = conn.execute(
                "SELECT * FROM tasks WHERE done = 0 AND due IS NOT NULL "
                "AND due <= ? ORDER BY due, id",
                (date_str,),
            ).fetchall()
        return [_row(r) for r in rows]

    def complete(self, task_id: int) -> bool:
        with closing(connect(self.path)) as conn:
            cur = conn.execute(
                "UPDATE tasks SET done = 1 WHERE id = ? AND done = 0", (task_id,)
            )
            conn.commit()
            return cur.rowcount > 0

    def delete(self, task_id: int) -> bool:
        with closing(connect(self.path)) as conn:
            cur = conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            conn.commit()
            return cur.rowcount > 0

    def clear(self) -> int:
        with closing(connect(self.path)) as conn:
            cur = conn.execute("DELETE FROM tasks")
            conn.commit()
            return cur.rowcount
