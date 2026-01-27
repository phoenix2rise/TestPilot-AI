from __future__ import annotations

from datetime import date, timedelta
from typing import Tuple


def next_weekday(start: date, weekday: int, *, include_today: bool = True) -> date:
    """Return the next occurrence of a weekday (0=Mon..6=Sun) from start."""
    if not 0 <= weekday <= 6:
        raise ValueError("weekday must be in range 0..6")
    days_ahead = (weekday - start.weekday()) % 7
    if days_ahead == 0 and not include_today:
        days_ahead = 7
    return start + timedelta(days=days_ahead)


def next_friday_to_monday_trip(start: date | None = None) -> Tuple[str, str]:
    """Return ISO dates for the next Friday check-in and following Monday checkout."""
    anchor = start or date.today()
    checkin = next_weekday(anchor, 4, include_today=True)
    checkout = next_weekday(checkin + timedelta(days=1), 0, include_today=True)
    return checkin.isoformat(), checkout.isoformat()
