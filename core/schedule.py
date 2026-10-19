"""Parse simple recurrence specs and decide when a job is due.

Supported forms (case-insensitive):
    every hour
    every day
    every day at 22:00
    every monday
    every sunday at 09:00

The check is period-based rather than exact-minute: ``should_run`` asks
"has a new scheduled boundary passed since we last ran?", so it works
whether the OS scheduler calls it every minute or once a day.
"""

from __future__ import annotations

import datetime as _dt
import re
from dataclasses import dataclass
from typing import Optional

_WEEKDAYS = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6,
}

_SPEC_RE = re.compile(
    r"^every\s+(?P<unit>hour|day|"
    r"monday|tuesday|wednesday|thursday|friday|saturday|sunday)"
    r"(?:\s+at\s+(?P<hour>\d{1,2}):(?P<minute>\d{2}))?$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Spec:
    kind: str  # "hourly" | "daily" | "weekly"
    hour: int = 9
    minute: int = 0
    weekday: Optional[int] = None  # 0 = Monday
    raw: str = ""

    def last_boundary(self, now: _dt.datetime) -> _dt.datetime:
        """The most recent scheduled instant at or before ``now``."""
        if self.kind == "hourly":
            return now.replace(minute=0, second=0, microsecond=0)

        target_time = now.replace(
            hour=self.hour, minute=self.minute, second=0, microsecond=0
        )
        if self.kind == "daily":
            if target_time > now:
                target_time -= _dt.timedelta(days=1)
            return target_time

        # weekly
        days_since = (now.weekday() - (self.weekday or 0)) % 7
        candidate = target_time - _dt.timedelta(days=days_since)
        if candidate > now:
            candidate -= _dt.timedelta(days=7)
        return candidate

    def should_run(self, last_run: Optional[_dt.datetime], now: _dt.datetime) -> bool:
        boundary = self.last_boundary(now)
        return last_run is None or last_run < boundary


def parse_spec(text: str) -> Optional[Spec]:
    match = _SPEC_RE.match(text.strip())
    if not match:
        return None
    unit = match.group("unit").lower()
    hour = int(match.group("hour")) if match.group("hour") else 9
    minute = int(match.group("minute")) if match.group("minute") else 0
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        return None
    if unit == "hour":
        return Spec(kind="hourly", raw=text.strip())
    if unit == "day":
        return Spec(kind="daily", hour=hour, minute=minute, raw=text.strip())
    return Spec(
        kind="weekly", hour=hour, minute=minute, weekday=_WEEKDAYS[unit], raw=text.strip()
    )
