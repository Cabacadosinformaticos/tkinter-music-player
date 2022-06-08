# Tests for the SQL Server history backend. pyodbc is never needed: a fake
# connection factory records the SQL and the parameters, and the config errors
# are checked with a temporary db_config.ini file.

from __future__ import annotations

import configparser
from datetime import date, datetime, time
from pathlib import Path

import pytest

from music_player.history.base import HistoryError
from music_player.history.sqlserver_backend import SqlServerHistory


class FakeCursor:
    """Minimal DB-API cursor: records every execute call and returns canned rows."""

    def __init__(self, rows: list[tuple] | None = None) -> None:
        self.executed: list[tuple[str, object]] = []
        self._rows = rows or []

    def execute(self, sql: str, params: object = None) -> "FakeCursor":
        """Remember the statement and its parameters."""
        self.executed.append((sql, params))
        return self

    def fetchall(self) -> list[tuple]:
        """Return the rows prepared for this cursor."""
        return list(self._rows)


class FakeConnection:
    """Minimal DB-API connection that hands out one fake cursor."""

    def __init__(self, rows: list[tuple] | None = None) -> None:
        self.cursor_obj = FakeCursor(rows)
        self.commits = 0
        self.closed = False

    def cursor(self) -> FakeCursor:
        """Return the fake cursor."""
        return self.cursor_obj

    def commit(self) -> None:
        """Count the commits."""
        self.commits += 1

    def close(self) -> None:
        """Mark the connection closed."""
        self.closed = True


class FakeFactory:
    """Connection factory used as the `connect` argument of the backend."""

    def __init__(self, connection: FakeConnection | None = None, error: Exception | None = None) -> None:
        self.connection = connection
        self.error = error
        self.strings: list[str] = []

    def __call__(self, connection_string: str) -> FakeConnection:
        """Record the connection string and return the fake connection."""
        self.strings.append(connection_string)
        if self.error is not None:
            raise self.error
        return self.connection


def write_config(path: Path, **overrides: str) -> Path:
    """Write a db_config.ini with a [database] section and the given values."""
    values = {
        "driver": "ODBC Driver 17 for SQL Server",
        "server": "localhost",
        "database": "music",
        "user": "sa",
        "password": "secret",
    }
    values.update(overrides)
    parser = configparser.ConfigParser()
    parser["database"] = values
    with path.open("w", encoding="utf-8") as handle:
        parser.write(handle)
    return path


# --- configuration errors ---

def test_missing_config_file_raises_history_error(tmp_path):
    history = SqlServerHistory(tmp_path / "db_config.ini")
    with pytest.raises(HistoryError) as info:
        history.entries()
    assert "db_config.ini" in str(info.value)


def test_missing_section_raises_history_error(tmp_path):
    path = tmp_path / "db_config.ini"
    path.write_text("[other]\nkey = value\n", encoding="utf-8")
    with pytest.raises(HistoryError) as info:
        SqlServerHistory(path).record("song")
    assert "db_config.ini" in str(info.value)


def test_missing_key_raises_history_error(tmp_path):
    path = tmp_path / "db_config.ini"
    parser = configparser.ConfigParser()
    parser["database"] = {"driver": "x", "server": "s", "database": "d", "user": "u"}
    with path.open("w", encoding="utf-8") as handle:
        parser.write(handle)
    with pytest.raises(HistoryError) as info:
        SqlServerHistory(path).entries()
    assert "db_config.ini" in str(info.value)


def test_connect_failure_becomes_history_error(tmp_path):
    path = write_config(tmp_path / "db_config.ini")
    factory = FakeFactory(error=RuntimeError("no server reachable"))
    history = SqlServerHistory(path, connect=factory)
    with pytest.raises(HistoryError) as info:
        history.record("song")
    assert "no server reachable" in str(info.value)


# --- connection and table setup ---

def test_connection_string_is_built_from_the_config(tmp_path):
    path = write_config(
        tmp_path / "db_config.ini",
        driver="ODBC Driver 18",
        server="host",
        database="db",
        user="me",
        password="pw",
    )
    factory = FakeFactory(FakeConnection())
    SqlServerHistory(path, connect=factory).entries()
    assert factory.strings == ["DRIVER={ODBC Driver 18};SERVER=host;DATABASE=db;UID=me;PWD=pw"]


def test_table_is_created_once_per_connection(tmp_path):
    path = write_config(tmp_path / "db_config.ini")
    connection = FakeConnection()
    history = SqlServerHistory(path, connect=FakeFactory(connection))
    history.record("a")
    history.record("b")
    history.entries()
    statements = [sql for sql, _ in connection.cursor_obj.executed]
    assert sum("OBJECT_ID" in sql for sql in statements) == 1
    assert sum("COL_LENGTH" in sql for sql in statements) == 1
    assert sum("ALTER TABLE music_history ADD Duration_seconds" in sql for sql in statements) == 1


# --- record, entries and clear ---

def test_record_uses_the_expected_sql_and_parameters(tmp_path):
    path = write_config(tmp_path / "db_config.ini")
    connection = FakeConnection()
    history = SqlServerHistory(path, connect=FakeFactory(connection))
    history.record("Song", datetime(2022, 6, 10, 21, 15, 3), 215.4)
    sql, params = connection.cursor_obj.executed[-1]
    assert "INSERT INTO music_history" in sql
    assert "Duration_seconds" in sql
    assert params == ("Song", "2022-06-10", "21:15:03", 215)


def test_record_default_time_and_duration(tmp_path):
    path = write_config(tmp_path / "db_config.ini")
    connection = FakeConnection()
    history = SqlServerHistory(path, connect=FakeFactory(connection))
    before = datetime.now()
    history.record("Song")
    after = datetime.now()
    _, params = connection.cursor_obj.executed[-1]
    assert params[0] == "Song"
    assert params[3] == 0
    recorded = datetime.fromisoformat(f"{params[1]}T{params[2]}")
    assert before.replace(microsecond=0) <= recorded <= after.replace(microsecond=0)


def test_entries_uses_the_expected_sql_and_parses_rows(tmp_path):
    path = write_config(tmp_path / "db_config.ini")
    rows = [
        ("New", date(2022, 6, 12), time(9, 30, 0), 12),
        ("Old", "2022-06-10", "21:15:03", None),
    ]
    connection = FakeConnection(rows)
    history = SqlServerHistory(path, connect=FakeFactory(connection))
    entries = history.entries()
    assert [entry.title for entry in entries] == ["New", "Old"]
    assert entries[0].played_at == datetime(2022, 6, 12, 9, 30, 0)
    assert entries[0].duration == 12.0
    assert entries[1].played_at == datetime(2022, 6, 10, 21, 15, 3)
    assert entries[1].duration == 0.0
    sql, params = connection.cursor_obj.executed[-1]
    assert "SELECT Music_name, Music_date, Music_time, Duration_seconds" in sql
    assert sql.endswith("ORDER BY Music_date DESC, Music_time DESC, Id DESC")
    assert params is None


def test_clear_uses_the_expected_sql(tmp_path):
    path = write_config(tmp_path / "db_config.ini")
    connection = FakeConnection()
    history = SqlServerHistory(path, connect=FakeFactory(connection))
    history.clear()
    sql, params = connection.cursor_obj.executed[-1]
    assert sql == "DELETE FROM music_history"
    assert params is None


def test_close_closes_the_connection(tmp_path):
    path = write_config(tmp_path / "db_config.ini")
    connection = FakeConnection()
    history = SqlServerHistory(path, connect=FakeFactory(connection))
    history.clear()
    history.close()
    assert connection.closed is True


def test_close_without_connection_is_safe(tmp_path):
    path = write_config(tmp_path / "db_config.ini")
    SqlServerHistory(path, connect=FakeFactory(FakeConnection())).close()


def test_describe_mentions_server_and_database(tmp_path):
    path = write_config(tmp_path / "db_config.ini", server="host", database="db")
    assert SqlServerHistory(path).describe() == "SQL Server: host/db"


def test_describe_with_missing_config_falls_back_to_the_label(tmp_path):
    history = SqlServerHistory(tmp_path / "db_config.ini")
    assert "db_config.ini" not in history.describe()
