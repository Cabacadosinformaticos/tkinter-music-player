# Tests for the SQLite history backend: recording, newest-first reading,
# persistence across reopenings, clear and the in-memory database.

from __future__ import annotations

from datetime import datetime

from music_player.history.sqlite_backend import SqliteHistory


def moment(text: str) -> datetime:
    """Helper: build a datetime from an ISO string."""
    return datetime.fromisoformat(text)


def test_fresh_database_has_no_entries(tmp_path):
    history = SqliteHistory(tmp_path / "history.db")
    assert history.entries() == []


def test_entries_are_newest_first(tmp_path):
    history = SqliteHistory(tmp_path / "history.db")
    history.record("old", moment("2022-06-10T10:00:00"), 10.0)
    history.record("new", moment("2022-06-12T10:00:00"), 20.0)
    history.record("middle", moment("2022-06-11T10:00:00"), 30.0)
    entries = history.entries()
    assert [entry.title for entry in entries] == ["new", "middle", "old"]
    assert [entry.duration for entry in entries] == [20.0, 30.0, 10.0]


def test_same_timestamp_returns_the_last_inserted_first(tmp_path):
    history = SqliteHistory(tmp_path / "history.db")
    history.record("first", moment("2022-06-10T10:00:00"), 1.0)
    history.record("second", moment("2022-06-10T10:00:00"), 2.0)
    assert [entry.title for entry in history.entries()] == ["second", "first"]


def test_default_time_is_now(tmp_path):
    history = SqliteHistory(tmp_path / "history.db")
    before = datetime.now()
    history.record("song")
    after = datetime.now()
    entry = history.entries()[0]
    assert before <= entry.played_at <= after
    assert entry.duration == 0.0


def test_persistence_across_reopening(tmp_path):
    path = tmp_path / "history.db"
    first = SqliteHistory(path)
    first.record("a", moment("2022-01-01T08:00:00"), 5.0)
    first.close()
    second = SqliteHistory(path)
    second.record("b", moment("2022-01-02T08:00:00"), 6.0)
    second.close()
    titles = [entry.title for entry in SqliteHistory(path).entries()]
    assert titles == ["b", "a"]


def test_clear_removes_every_entry(tmp_path):
    path = tmp_path / "history.db"
    history = SqliteHistory(path)
    history.record("a", moment("2022-01-01T08:00:00"), 5.0)
    history.record("b", moment("2022-01-02T08:00:00"), 6.0)
    history.clear()
    assert history.entries() == []
    history.close()
    assert SqliteHistory(path).entries() == []


def test_in_memory_database_works():
    history = SqliteHistory(":memory:")
    history.record("song", moment("2022-01-01T08:00:00"), 3.0)
    entries = history.entries()
    assert [entry.title for entry in entries] == ["song"]
    history.clear()
    assert history.entries() == []
    history.close()


def test_unicode_title_round_trip(tmp_path):
    history = SqliteHistory(tmp_path / "history.db")
    history.record("Canção - João", moment("2022-01-01T08:00:00"), 1.0)
    assert history.entries()[0].title == "Canção - João"


def test_describe_mentions_the_file(tmp_path):
    path = tmp_path / "history.db"
    assert str(path) in SqliteHistory(path).describe()
