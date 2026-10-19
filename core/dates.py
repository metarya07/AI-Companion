"""Parse small natural-language dates like "tomorrow" or "friday".

Kept deliberately tiny and dependency-free. ``today`` is injectable so
tests are deterministic. Returns an ISO ``YYYY-MM-DD`` string or None.
"""

from __future__ import annotations

import datetime as _dt
import re
from typing import Optional

_WEEKDAYS = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6,
    "mon": 0, "tue": 1, "tues": 1, "wed": 2, "thu": 3, "thur": 3,
    "thurs": 3, "fri": 4, "sat": 5, "sun": 6,
}

_ISO_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_IN_DAYS_RE = re.compile(r"^in\s+(\d+)\s+days?$", re.IGNORECASE)


def parse_due(text: str, today: Optional[_dt.date] = None) -> Optional[str]:
    today = today or _dt.date.today()
    t = text.strip().lower()
    if not t:
        return None

    if t == "today":
        return today.isoformat()
    if t == "tomorrow":
        return (today + _dt.timedelta(days=1)).isoformat()

    in_days = _IN_DAYS_RE.match(t)
    if in_days:
        return (today + _dt.timedelta(days=int(in_days.group(1)))).isoformat()

    if _ISO_RE.match(t):
        try:
            return _dt.date.fromisoformat(t).isoformat()
        except ValueError:
            return None

    if t in _WEEKDAYS:
        target = _WEEKDAYS[t]
        # The next occurrence of that weekday (today counts only if it's later
        # in the week; "friday" said on Friday means next Friday).
        delta = (target - today.weekday()) % 7
        delta = delta or 7
        return (today + _dt.timedelta(days=delta)).isoformat()

    return None
