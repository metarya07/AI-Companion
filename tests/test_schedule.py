"""parse_spec + Spec.should_run drive the automation scheduler."""

from __future__ import annotations

import datetime as _dt

import pytest

from core.schedule import parse_spec


def test_parse_hourly():
    spec = parse_spec("every hour")
    assert spec.kind == "hourly"


def test_parse_daily_default_and_timed():
    assert parse_spec("every day").kind == "daily"
    timed = parse_spec("every day at 22:00")
    assert (timed.kind, timed.hour, timed.minute) == ("daily", 22, 0)


def test_parse_weekly():
    spec = parse_spec("every monday at 7:30")
    assert (spec.kind, spec.weekday, spec.hour, spec.minute) == ("weekly", 0, 7, 30)
    assert parse_spec("every sunday").weekday == 6


@pytest.mark.parametrize("bad", ["", "every fortnight", "daily", "every day at 25:00"])
def test_parse_rejects_garbage(bad):
    assert parse_spec(bad) is None


def test_hourly_should_run():
    spec = parse_spec("every hour")
    now = _dt.datetime(2026, 6, 14, 10, 15)
    assert spec.should_run(None, now) is True
    assert spec.should_run(_dt.datetime(2026, 6, 14, 10, 5), now) is False
    assert spec.should_run(_dt.datetime(2026, 6, 14, 9, 59), now) is True


def test_daily_should_run_after_boundary():
    spec = parse_spec("every day at 22:00")
    now = _dt.datetime(2026, 6, 14, 23, 0)
    assert spec.should_run(None, now) is True
    assert spec.should_run(_dt.datetime(2026, 6, 14, 22, 30), now) is False
    assert spec.should_run(_dt.datetime(2026, 6, 13, 22, 0), now) is True


def test_daily_before_boundary_uses_yesterday():
    spec = parse_spec("every day at 22:00")
    now = _dt.datetime(2026, 6, 14, 21, 0)  # before today's 22:00
    # Already ran after yesterday's 22:00 boundary -> not due yet.
    assert spec.should_run(_dt.datetime(2026, 6, 13, 23, 0), now) is False


def test_weekly_should_run():
    spec = parse_spec("every sunday at 09:00")
    now = _dt.datetime(2026, 6, 14, 10, 0)  # Sunday, after 09:00
    assert spec.should_run(None, now) is True
    assert spec.should_run(_dt.datetime(2026, 6, 14, 9, 30), now) is False
    assert spec.should_run(_dt.datetime(2026, 6, 7, 9, 0), now) is True
