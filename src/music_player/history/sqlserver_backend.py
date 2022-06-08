# SQL Server history backend: keeps the plays in the same music_history table
# used by the database version of the player. pyodbc is imported only when a
# connection is really needed, so the app works without it.

from __future__ import annotations

import configparser
from datetime import date, datetime, time
from pathlib import Path

from ..config import DB_CONFIG_FILE
from .base import HistoryBackend, HistoryEntry, HistoryError

# Section and keys read from db_config.ini.
_SECTION = "database"
_KEYS = ("driver", "server", "database", "user", "password")

# SQL used by this backend.
_READ_SQL = (
    "SELECT Music_name, Music_date, Music_time, Duration_seconds "
    "FROM music_history ORDER BY Music_date DESC, Music_time DESC, Id DESC"
)
_INSERT_SQL = (
    "INSERT INTO music_history (Music_name, Music_date, Music_time, Duration_seconds) "
    "VALUES (?, ?, ?, ?)"
)
_DELETE_SQL = "DELETE FROM music_history"
_ENSURE_TABLE_SQL = (
    "IF OBJECT_ID(N'music_history', N'U') IS NULL "
    "CREATE TABLE music_history (Id INT IDENTITY(1,1) PRIMARY KEY, "
    "Music_name NVARCHAR(255) NOT NULL, Music_date DATE NOT NULL, Music_time TIME(0) NOT NULL)"
)
_ENSURE_COLUMN_SQL = (
    "IF COL_LENGTH('music_history', 'Duration_seconds') IS NULL "
    "ALTER TABLE music_history ADD Duration_seconds INT NULL"
)


def _row_datetime(day: object, moment: object) -> datetime:
    """Build a datetime from the two columns, accepting date/time objects or ISO text."""
    if not isinstance(day, date):
        day = date.fromisoformat(str(day))
    if isinstance(moment, time):
        clock = moment
    else:
        clock = time.fromisoformat(str(moment))
    return datetime.combine(day, clock)


class SqlServerHistory(HistoryBackend):
    """Play history stored in a SQL Server table, connected on first use."""

    name = "sqlserver"
    label = "SQL Server"

    def __init__(self, config_path: Path, connect=None) -> None:
        """Keep the db_config.ini path and an optional connection factory used by tests."""
        self.config_path = Path(config_path)
        self._connect_factory = connect
        self._connection = None
        self._table_checked = False

    def _settings(self) -> dict[str, str]:
        """Read the [database] section of db_config.ini, or raise HistoryError."""
        if not self.config_path.exists():
            raise HistoryError(
                "db_config.ini not found. Copy db_config.example.ini to db_config.ini "
                f"and fill in the database details ({self.config_path})."
            )
        parser = configparser.ConfigParser(interpolation=None)
        try:
            parser.read(self.config_path, encoding="utf-8")
        except (OSError, configparser.Error) as error:
            raise HistoryError(f"Could not read db_config.ini: {error}")
        if not parser.has_section(_SECTION):
            raise HistoryError("Missing [database] section in db_config.ini")
        values = {}
        for key in _KEYS:
            if not parser.has_option(_SECTION, key):
                raise HistoryError(
                    f"Missing {key!r} key in the [database] section of db_config.ini"
                )
            values[key] = parser.get(_SECTION, key)
        return values

    def _connection_string(self, settings: dict[str, str]) -> str:
        """ODBC connection string built like the old database player does."""
        return "DRIVER={%s};SERVER=%s;DATABASE=%s;UID=%s;PWD=%s" % (
            settings["driver"],
            settings["server"],
            settings["database"],
            settings["user"],
            settings["password"],
        )

    def _connect(self):
        """Open the connection on first use and reuse it afterwards."""
        if self._connection is not None:
            return self._connection
        settings = self._settings()
        connection_string = self._connection_string(settings)
        try:
            if self._connect_factory is not None:
                self._connection = self._connect_factory(connection_string)
            else:
                # pyodbc is imported here only, so the rest of the app does not need it.
                import pyodbc

                self._connection = pyodbc.connect(connection_string, timeout=5)
        except Exception as error:
            raise HistoryError(f"Could not connect to the database: {error}")
        self._ensure_table()
        return self._connection

    def _ensure_table(self) -> None:
        """Create the table and the Duration_seconds column when missing, once per connection."""
        if self._table_checked:
            return
        cursor = self._connection.cursor()
        cursor.execute(_ENSURE_TABLE_SQL)
        cursor.execute(_ENSURE_COLUMN_SQL)
        self._connection.commit()
        self._table_checked = True

    def record(
        self, title: str, played_at: datetime | None = None, duration: float = 0.0
    ) -> None:
        """Insert one play, with the day and time as text and the duration as whole seconds."""
        if played_at is None:
            played_at = datetime.now()
        connection = self._connect()
        cursor = connection.cursor()
        cursor.execute(
            _INSERT_SQL,
            (
                str(title),
                played_at.strftime("%Y-%m-%d"),
                played_at.strftime("%H:%M:%S"),
                int(duration),
            ),
        )
        connection.commit()

    def entries(self) -> list[HistoryEntry]:
        """Read every play, newest first; dates and times may come as objects or text."""
        connection = self._connect()
        cursor = connection.cursor()
        cursor.execute(_READ_SQL)
        result = []
        for row in cursor.fetchall():
            result.append(
                HistoryEntry(
                    title=str(row[0]),
                    played_at=_row_datetime(row[1], row[2]),
                    duration=float(row[3] or 0.0),
                )
            )
        return result

    def clear(self) -> None:
        """Delete every play from the table."""
        connection = self._connect()
        cursor = connection.cursor()
        cursor.execute(_DELETE_SQL)
        connection.commit()

    def close(self) -> None:
        """Close the connection when it was opened."""
        if self._connection is not None:
            try:
                self._connection.close()
            except Exception:
                pass
            self._connection = None
            self._table_checked = False

    def describe(self) -> str:
        """Server and database read from the config, or the label when it cannot be read."""
        try:
            settings = self._settings()
        except HistoryError:
            return self.label
        return f"SQL Server: {settings['server']}/{settings['database']}"
