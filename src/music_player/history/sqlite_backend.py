# SQLite history backend: the plays are kept in a small database file with a
# single table. It is the default backend because it needs no server.

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

from .base import HistoryBackend, HistoryEntry

# Table used by this backend, created when the database is opened.
_SCHEMA = """
CREATE TABLE IF NOT EXISTS plays (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    played_at TEXT NOT NULL,
    duration REAL NOT NULL DEFAULT 0
)
"""


class SqliteHistory(HistoryBackend):
    """Play history stored in a SQLite database; the path may be ":memory:"."""

    name = "sqlite"
    label = "SQLite database"

    def __init__(self, path: Path | str) -> None:
        """Open the database, creating the file and the table when needed."""
        self.path = path
        self._target = str(path)
        self._connection = sqlite3.connect(self._target)
        self._connection.execute(_SCHEMA)
        self._connection.commit()

    def record(
        self, title: str, played_at: datetime | None = None, duration: float = 0.0
    ) -> None:
        """Insert one play; a None `played_at` means the current moment."""
        if played_at is None:
            played_at = datetime.now()
        self._connection.execute(
            "INSERT INTO plays (title, played_at, duration) VALUES (?, ?, ?)",
            (str(title), played_at.isoformat(), float(duration)),
        )
        self._connection.commit()

    def entries(self) -> list[HistoryEntry]:
        """Read every play, newest first."""
        rows = self._connection.execute(
            "SELECT title, played_at, duration FROM plays ORDER BY played_at DESC, id DESC"
        ).fetchall()
        result = []
        for title, played_at, duration in rows:
            try:
                moment = datetime.fromisoformat(str(played_at))
            except ValueError:
                continue
            result.append(
                HistoryEntry(title=str(title), played_at=moment, duration=float(duration))
            )
        return result

    def clear(self) -> None:
        """Delete every play from the database."""
        self._connection.execute("DELETE FROM plays")
        self._connection.commit()

    def close(self) -> None:
        """Close the database connection."""
        self._connection.close()

    def describe(self) -> str:
        """Path of the database file that holds the history."""
        return f"SQLite database: {self._target}"
