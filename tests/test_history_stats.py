# Tests for the history statistics: top songs with ties, listening time per
# day with zero filling and the total listening time.

from __future__ import annotations

from datetime import date, datetime, timedelta

from music_player.history.base import HistoryEntry
from music_player.history.stats import (
    listening_by_day,
    top_songs,
    total_listening_seconds,
)


def entry(title: str, when: str, duration: float = 0.0) -> HistoryEntry:
    """Helper: build a HistoryEntry from a title, an ISO moment and a duration."""
    return HistoryEntry(title=title, played_at=datetime.fromisoformat(when), duration=duration)


# --- top_songs ---

def test_top_songs_counts_and_orders_by_plays():
    entries = [
        entry("A", "2022-06-10T10:00:00"),
        entry("B", "2022-06-10T11:00:00"),
        entry("A", "2022-06-11T10:00:00"),
        entry("C", "2022-06-11T11:00:00"),
        entry("B", "2022-06-12T11:00:00"),
        entry("B", "2022-06-12T12:00:00"),
    ]
    assert top_songs(entries) == [("B", 3), ("A", 2), ("C", 1)]


def test_top_songs_breaks_ties_by_title():
    entries = [
        entry("Zebra", "2022-06-10T10:00:00"),
        entry("Alpha", "2022-06-10T11:00:00"),
        entry("Mike", "2022-06-10T12:00:00"),
    ]
    assert top_songs(entries) == [("Alpha", 1), ("Mike", 1), ("Zebra", 1)]


def test_top_songs_honours_the_limit():
    entries = [
        entry("A", "2022-06-10T10:00:00"),
        entry("B", "2022-06-10T11:00:00"),
        entry("A", "2022-06-11T10:00:00"),
    ]
    assert top_songs(entries, limit=1) == [("A", 2)]


def test_top_songs_of_empty_list_is_empty():
    assert top_songs([]) == []


# --- listening_by_day ---

def test_listening_by_day_zero_fills_and_has_exact_length():
    entries = [
        entry("A", "2022-06-10T10:00:00", 30.0),
        entry("B", "2022-06-10T12:00:00", 10.0),
        entry("C", "2022-06-12T09:00:00", 5.0),
    ]
    days = listening_by_day(entries, days=4, today=date(2022, 6, 13))
    assert len(days) == 4
    assert days[0] == (date(2022, 6, 10), 40.0)
    assert days[1] == (date(2022, 6, 11), 0.0)
    assert days[2] == (date(2022, 6, 12), 5.0)
    assert days[3] == (date(2022, 6, 13), 0.0)


def test_listening_by_day_is_oldest_first_and_ends_today():
    days = listening_by_day([], days=3)
    today = date.today()
    assert [day for day, _ in days] == [
        today - timedelta(days=2),
        today - timedelta(days=1),
        today,
    ]


def test_listening_by_day_ignores_entries_outside_the_window():
    entries = [
        entry("old", "2022-06-01T10:00:00", 100.0),
        entry("new", "2022-06-13T10:00:00", 7.0),
        entry("future", "2022-06-20T10:00:00", 50.0),
    ]
    days = listening_by_day(entries, days=2, today=date(2022, 6, 13))
    assert days == [(date(2022, 6, 12), 0.0), (date(2022, 6, 13), 7.0)]


def test_listening_by_day_with_zero_days_is_empty():
    assert listening_by_day([entry("A", "2022-06-10T10:00:00", 1.0)], days=0) == []


# --- total_listening_seconds ---

def test_total_listening_seconds_sums_every_duration():
    entries = [
        entry("A", "2022-06-10T10:00:00", 30.5),
        entry("B", "2022-06-10T12:00:00", 10.0),
        entry("C", "2022-06-12T09:00:00", 0.5),
    ]
    assert total_listening_seconds(entries) == 41.0


def test_total_listening_seconds_of_empty_list_is_zero():
    assert total_listening_seconds([]) == 0.0
