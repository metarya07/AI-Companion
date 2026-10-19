"""Stored schedules for the automation agent.

A schedule pairs a JARVIS command with a recurrence spec (e.g. "every
sunday at 09:00"). An OS scheduler (cron / Task Scheduler) runs
``jarvis --run-due`` periodically; that command checks these rows and
runs any whose period has elapsed since ``last_run``.
"""

from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Union

from memory.store import connect, ensure_parent


@dataclass(frozen=True)
class Schedule:
    id: int
    command: str
    spec: str
    last_run: Optional[str]
    created_at: str


_SCHEMA = """
CREATE TABLE IF NOT EXISTS schedules (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    command    TEXT NOT NULL,
    spec       TEXT NOT NULL,
    last_run   TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""


def _row(r) -> Schedule:
    return Schedule(r["id"], r["command"], r["spec"], r["last_run"], r["created_at"])


class ScheduleStore:
    def __init__(self, path: Union[str, Path]) -> None:
        self.path = str(path)
        ensure_parent(self.path)
        with closing(connect(self.path)) as conn:
            conn.execute(_SCHEMA)
            conn.commit()

    def add(self, command: str, spec: str) -> int:
        with closing(connect(self.path)) as conn:
            cur = conn.execute(
                "INSERT INTO schedules (command, spec) VALUES (?, ?)",
                (command.strip(), spec.strip()),
            )
            conn.commit()
            return int(cur.lastrowid)

    def all(self) -> List[Schedule]:
        with closing(connect(self.path)) as conn:
            rows = conn.execute("SELECT * FROM schedules ORDER BY id").fetchall()
        return [_row(r) for r in rows]

    def mark_run(self, schedule_id: int, when_iso: str) -> None:
        with closing(connect(self.path)) as conn:
            conn.execute(
                "UPDATE schedules SET last_run = ? WHERE id = ?",
                (when_iso, schedule_id),
            )
            conn.commit()

    def delete(self, schedule_id: int) -> bool:
        with closing(connect(self.path)) as conn:
            cur = conn.execute("DELETE FROM schedules WHERE id = ?", (schedule_id,))
            conn.commit()
            return cur.rowcount > 0

    def clear(self) -> int:
        with closing(connect(self.path)) as conn:
            cur = conn.execute("DELETE FROM schedules")
            conn.commit()
            return cur.rowcount
