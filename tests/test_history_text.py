# Tests for the text history backend: recording, newest-first reading,
# persistence across reopenings, clear, title cleaning and malformed lines.

from __future__ import annotations

from datetime import datetime

import pytest

from music_player.history.text_backend import TextHistory


def moment(text: str) -> datetime:
    """Helper: build a datetime from an ISO string."""
    return datetime.fromisoformat(text)


def test_new_file_has_no_entries(tmp_path):
    history = TextHistory(tmp_path / "history.txt")
    assert history.entries() == []


def test_missing_file_has_no_entries(tmp_path):
    history = TextHistory(tmp_path / "not_created.txt")
    assert history.entries() == []


def test_entries_are_newest_first(tmp_path):
    history = TextHistory(tmp_path / "history.txt")
    history.record("old", moment("2022-06-10T10:00:00"), 10.0)
    history.record("new", moment("2022-06-12T10:00:00"), 20.0)
    history.record("middle", moment("2022-06-11T10:00:00"), 30.0)
    entries = history.entries()
    assert [entry.title for entry in entries] == ["new", "middle", "old"]
    assert [entry.duration for entry in entries] == [20.0, 30.0, 10.0]


def test_same_timestamp_keeps_the_last_written_first(tmp_path):
    history = TextHistory(tmp_path / "history.txt")
    history.record("first", moment("2022-06-10T10:00:00"), 1.0)
    history.record("second", moment("2022-06-10T10:00:00"), 2.0)
    assert [entry.title for entry in history.entries()] == ["second", "first"]


def test_default_time_is_now(tmp_path):
    history = TextHistory(tmp_path / "history.txt")
    before = datetime.now()
    history.record("song")
    after = datetime.now()
    entry = history.entries()[0]
    assert before <= entry.played_at <= after
    assert entry.duration == 0.0


def test_persistence_across_reopening(tmp_path):
    path = tmp_path / "history.txt"
    first = TextHistory(path)
    first.record("a", moment("2022-01-01T08:00:00"), 5.0)
    second = TextHistory(path)
    second.record("b", moment("2022-01-02T08:00:00"), 6.0)
    titles = [entry.title for entry in TextHistory(path).entries()]
    assert titles == ["b", "a"]


def test_clear_removes_every_entry(tmp_path):
    path = tmp_path / "history.txt"
    history = TextHistory(path)
    history.record("a", moment("2022-01-01T08:00:00"), 5.0)
    history.record("b", moment("2022-01-02T08:00:00"), 6.0)
    history.clear()
    assert history.entries() == []
    assert TextHistory(path).entries() == []


def test_title_with_tabs_and_newlines_is_cleaned(tmp_path):
    path = tmp_path / "history.txt"
    history = TextHistory(path)
    history.record("Tab\there\nnew line", moment("2022-01-01T08:00:00"), 1.0)
    raw = path.read_text(encoding="utf-8")
    # One line ending only, and the two separators.
    assert raw.count("\n") == 1
    assert raw.count("\t") == 2
    assert history.entries()[0].title == "Tab here new line"


def test_unicode_title_round_trip(tmp_path):
    history = TextHistory(tmp_path / "history.txt")
    history.record("Canção - João", moment("2022-01-01T08:00:00"), 1.0)
    assert history.entries()[0].title == "Canção - João"


def test_malformed_lines_are_skipped(tmp_path):
    path = tmp_path / "history.txt"
    path.write_text(
        "not a date\t5\tbad\n"
        "2022-06-10T21:15:03\tnot a number\tbad\n"
        "only two\tfields\n"
        "\n"
        "2022-06-10T21:15:03\t215.4\tGood\n",
        encoding="utf-8",
    )
    entries = TextHistory(path).entries()
    assert [entry.title for entry in entries] == ["Good"]
    assert entries[0].duration == pytest.approx(215.4)


def test_describe_mentions_the_file(tmp_path):
    path = tmp_path / "history.txt"
    assert str(path) in TextHistory(path).describe()
