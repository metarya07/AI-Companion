"""Shared fixtures.

The database fixtures use a real file under pytest's ``tmp_path`` rather
than an in-memory SQLite database on purpose: ``Database`` opens a fresh
connection per call, and separate connections to ``:memory:`` would each
see an empty database. A throwaway file behaves exactly like production
while still being isolated and auto-cleaned.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from config.settings import Settings
from memory.database import Database


@pytest.fixture
def db_path(tmp_path) -> Path:
    return tmp_path / "jarvis_test.db"


@pytest.fixture
def database(db_path) -> Database:
    return Database(db_path)


@pytest.fixture
def settings(db_path) -> Settings:
    """Settings wired for tests: isolated DB, no real launching, AI off."""
    return Settings(db_path=db_path, dry_run=True, ai_provider="none")
