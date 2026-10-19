"""parse_due turns small natural dates into ISO strings."""

from __future__ import annotations

import datetime as _dt

from core.dates import parse_due

# A fixed Sunday so weekday maths is deterministic.
TODAY = _dt.date(2026, 6, 14)


def test_today_and_tomorrow():
    assert parse_due("today", TODAY) == "2026-06-14"
    assert parse_due("tomorrow", TODAY) == "2026-06-15"


def test_iso_passthrough():
    assert parse_due("2026-06-20", TODAY) == "2026-06-20"


def test_invalid_iso_is_none():
    assert parse_due("2026-13-40", TODAY) is None


def test_in_n_days():
    assert parse_due("in 3 days", TODAY) == "2026-06-17"


def test_weekday_picks_next_occurrence():
    # Friday after Sunday 14 June is the 19th.
    assert parse_due("friday", TODAY) == "2026-06-19"


def test_same_weekday_rolls_to_next_week():
    # "sunday" said on a Sunday means next Sunday.
    assert parse_due("sunday", TODAY) == "2026-06-21"


def test_unparseable_and_empty():
    assert parse_due("someday", TODAY) is None
    assert parse_due("", TODAY) is None
