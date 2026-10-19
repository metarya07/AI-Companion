"""User preferences (key/value) for the memory agent."""

from __future__ import annotations

from contextlib import closing
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

from memory.store import connect, ensure_parent

_SCHEMA = """
CREATE TABLE IF NOT EXISTS prefs (
    key        TEXT PRIMARY KEY,
    value      TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""


class PrefStore:
    def __init__(self, path: Union[str, Path]) -> None:
        self.path = str(path)
        ensure_parent(self.path)
        with closing(connect(self.path)) as conn:
            conn.execute(_SCHEMA)
            conn.commit()

    def set(self, key: str, value: str) -> None:
        with closing(connect(self.path)) as conn:
            conn.execute(
                "INSERT INTO prefs (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value, "
                "updated_at = CURRENT_TIMESTAMP",
                (key.strip().lower(), value.strip()),
            )
            conn.commit()

    def get(self, key: str) -> Optional[str]:
        with closing(connect(self.path)) as conn:
            row = conn.execute(
                "SELECT value FROM prefs WHERE key = ?", (key.strip().lower(),)
            ).fetchone()
        return row["value"] if row else None

    def all(self) -> List[Tuple[str, str]]:
        with closing(connect(self.path)) as conn:
            rows = conn.execute(
                "SELECT key, value FROM prefs ORDER BY key"
            ).fetchall()
        return [(r["key"], r["value"]) for r in rows]

    def delete(self, key: str) -> bool:
        with closing(connect(self.path)) as conn:
            cur = conn.execute("DELETE FROM prefs WHERE key = ?", (key.strip().lower(),))
            conn.commit()
            return cur.rowcount > 0

    def clear(self) -> int:
        with closing(connect(self.path)) as conn:
            cur = conn.execute("DELETE FROM prefs")
            conn.commit()
            return cur.rowcount
