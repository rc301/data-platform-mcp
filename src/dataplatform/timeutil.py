"""Shared time helpers. Any tool/command that shows timestamps to the data
engineer formats them in BRT through here, so the convention lives in one place.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

# Brazil has had no DST since 2019, so a fixed -03:00 offset is correct.
BRT = timezone(timedelta(hours=-3), "BRT")


def fmt_brt(value: datetime | None) -> str | None:
    """Format a (UTC or naive-UTC) datetime as ``YYYY-MM-DD HH:MM:SS BRT``."""
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(BRT).strftime("%Y-%m-%d %H:%M:%S %Z")
