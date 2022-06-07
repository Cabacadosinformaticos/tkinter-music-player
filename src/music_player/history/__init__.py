# History package: the storage backends for the play history and the factory that
# builds the one chosen in the settings.

from __future__ import annotations

from pathlib import Path

from ..config import data_dir
from .base import HistoryBackend, HistoryEntry, HistoryError
from .sqlite_backend import SqliteHistory
from .text_backend import TextHistory

# Names accepted by the settings and the class that implements each one.
BACKENDS = {"sqlite": SqliteHistory, "text": TextHistory}

__all__ = [
    "BACKENDS",
    "HistoryBackend",
    "HistoryEntry",
    "HistoryError",
    "SqliteHistory",
    "TextHistory",
    "make_backend",
]


def make_backend(kind: str, data_path: Path | None = None) -> HistoryBackend:
    """Build the backend named by `kind`; an unknown kind raises ValueError."""
    if kind not in BACKENDS:
        raise ValueError(f"unknown history backend: {kind!r}")
    folder = Path(data_path) if data_path is not None else data_dir()
    if kind == "sqlite":
        return SqliteHistory(folder / "history.db")
    return TextHistory(folder / "history.txt")
