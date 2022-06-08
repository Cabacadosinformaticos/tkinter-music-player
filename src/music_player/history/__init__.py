# History package: the storage backends for the play history and the factory that
# builds the one chosen in the settings. Importing this package never imports
# pyodbc; that only happens when a SQL Server connection is really opened.

from __future__ import annotations

from pathlib import Path

from ..config import DB_CONFIG_FILE, data_dir
from .base import HistoryBackend, HistoryEntry, HistoryError
from .sqlite_backend import SqliteHistory
from .sqlserver_backend import SqlServerHistory
from .text_backend import TextHistory

# Names accepted by the settings and the class that implements each one.
BACKENDS = {"sqlite": SqliteHistory, "text": TextHistory, "sqlserver": SqlServerHistory}

__all__ = [
    "BACKENDS",
    "HistoryBackend",
    "HistoryEntry",
    "HistoryError",
    "SqlServerHistory",
    "SqliteHistory",
    "TextHistory",
    "make_backend",
]


def make_backend(
    kind: str, data_path: Path | None = None, db_config_path: Path | None = None
) -> HistoryBackend:
    """Build the backend named by `kind`; an unknown kind raises ValueError."""
    if kind not in BACKENDS:
        raise ValueError(f"unknown history backend: {kind!r}")
    if kind == "sqlserver":
        path = Path(db_config_path) if db_config_path is not None else DB_CONFIG_FILE
        return SqlServerHistory(path)
    folder = Path(data_path) if data_path is not None else data_dir()
    if kind == "sqlite":
        return SqliteHistory(folder / "history.db")
    return TextHistory(folder / "history.txt")
