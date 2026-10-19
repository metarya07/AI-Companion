"""Tiny shared SQLite helpers.

Several stores (memories, tasks, preferences, history, schedules) all live
in the same database file. They share these helpers so connection setup
and the "create the parent folder" logic exist in exactly one place.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Union


def ensure_parent(path: Union[str, Path]) -> None:
    """Create the directory that will hold ``path`` if it doesn't exist."""
    parent = Path(path).parent
    if str(parent) and parent != Path("."):
        parent.mkdir(parents=True, exist_ok=True)


def connect(path: Union[str, Path]) -> sqlite3.Connection:
    """Open a connection with row access by column name."""
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    return conn
