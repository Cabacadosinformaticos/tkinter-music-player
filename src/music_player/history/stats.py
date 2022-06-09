# History statistics: pure functions over a list of HistoryEntry, used by the
# stats window to show the most played songs and the listening time per day.

from __future__ import annotations

from collections import Counter
from datetime import date, timedelta

from .base import HistoryEntry


def top_songs(entries: list[HistoryEntry], limit: int = 10) -> list[tuple[str, int]]:
    """Most played titles as (title, plays), most plays first and then title A-Z."""
    counts = Counter(entry.title for entry in entries)
    ordered = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return ordered[:limit]


def listening_by_day(
    entries: list[HistoryEntry], days: int = 14, today: date | None = None
) -> list[tuple[date, float]]:
    """Seconds listened on each of the last `days` days, oldest first, zero filled."""
    if days <= 0:
        return []
    if today is None:
        today = date.today()
    totals: dict[date, float] = {}
    for entry in entries:
        day = entry.played_at.date()
        totals[day] = totals.get(day, 0.0) + entry.duration
    start = today - timedelta(days=days - 1)
    result = []
    for offset in range(days):
        day = start + timedelta(days=offset)
        result.append((day, totals.get(day, 0.0)))
    return result


def total_listening_seconds(entries: list[HistoryEntry]) -> float:
    """Sum of the durations of every play, in seconds."""
    return sum(entry.duration for entry in entries)
