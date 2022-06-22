# Tests for the data behind the statistics window: the summary built from a list
# of plays and the listening time formatter. No Tk window is created here, only
# the module is imported, so the tests run without a display.

from __future__ import annotations

from datetime import date, datetime, timedelta

from music_player.history.base import HistoryEntry
from music_player.stats_window import format_listening_time, summarize

# Day used as "today" in the tests, so the daily window is deterministic.
TODAY = date(2022, 6, 20)


def entry(title: str, when: str, duration: float = 0.0) -> HistoryEntry:
    """Helper: build a HistoryEntry from a title, an ISO moment and a duration."""
    return HistoryEntry(title=title, played_at=datetime.fromisoformat(when), duration=duration)


# --- summarize ---

def test_summarize_counts_plays_total_and_distinct_songs():
    entries = [
        entry("A", "2022-06-19T10:00:00", 30.0),
        entry("B", "2022-06-19T11:00:00", 10.0),
        entry("A", "2022-06-20T10:00:00", 20.0),
    ]
    summary = summarize(entries, today=TODAY)
    assert summary.plays == 3
    assert summary.total_seconds == 60.0
    assert summary.distinct == 2


def test_summarize_keeps_the_top_songs_ordered_by_plays():
    entries = [
        entry("B", "2022-06-20T10:00:00", 1.0),
        entry("B", "2022-06-20T11:00:00", 1.0),
        entry("A", "2022-06-20T12:00:00", 1.0),
    ]
    summary = summarize(entries, today=TODAY)
    assert summary.top == [("B", 2), ("A", 1)]


def test_summarize_limits_the_top_songs():
    entries = [
        entry(f"Song {index}", "2022-06-20T10:00:00", 1.0) for index in range(12)
    ]
    assert len(summarize(entries, today=TODAY).top) == 8
    assert len(summarize(entries, today=TODAY, limit=3).top) == 3


def test_summarize_daily_has_one_value_per_day_ending_today():
    entries = [
        entry("A", "2022-06-20T10:00:00", 30.0),
        entry("B", "2022-06-19T12:00:00", 60.0),
        entry("old", "2022-06-01T12:00:00", 999.0),
    ]
    daily = summarize(entries, today=TODAY).daily
    assert len(daily) == 14
    assert daily[0][0] == TODAY - timedelta(days=13)
    assert daily[-1] == (TODAY, 30.0)
    assert daily[-2] == (TODAY - timedelta(days=1), 60.0)
    # The play outside the window is not counted anywhere.
    assert sum(seconds for _day, seconds in daily) == 90.0


def test_summarize_of_no_plays_is_all_empty():
    summary = summarize([], today=TODAY)
    assert summary.plays == 0
    assert summary.total_seconds == 0.0
    assert summary.distinct == 0
    assert summary.top == []
    assert len(summary.daily) == 14
    assert all(seconds == 0.0 for _day, seconds in summary.daily)


# --- format_listening_time ---

def test_format_listening_time_in_hours_and_minutes():
    assert format_listening_time(3 * 3600 + 12 * 60) == "3 h 12 min"


def test_format_listening_time_in_minutes_only():
    assert format_listening_time(42 * 60) == "42 min"


def test_format_listening_time_of_zero():
    assert format_listening_time(0) == "0 min"


def test_format_listening_time_under_one_minute_is_zero_minutes():
    assert format_listening_time(59) == "0 min"


def test_format_listening_time_ignores_negative_values():
    assert format_listening_time(-10) == "0 min"


def test_format_listening_time_of_a_full_hour():
    assert format_listening_time(3600) == "1 h 0 min"
