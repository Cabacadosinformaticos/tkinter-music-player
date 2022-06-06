# History package base: the HistoryError exception, the HistoryEntry record and
# the HistoryBackend interface shared by the text, SQLite and SQL Server backends.

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


class HistoryError(Exception):
    """Friendly error raised when the play history cannot be read or written."""


@dataclass
class HistoryEntry:
    """One play: the song title, the moment it was played and its length in seconds."""

    title: str
    played_at: datetime
    duration: float = 0.0


class HistoryBackend(ABC):
    """Interface of a play history store; each subclass keeps the data somewhere else."""

    name: str = ""
    label: str = "History"

    @abstractmethod
    def record(self, title: str, played_at: datetime | None = None, duration: float = 0.0) -> None:
        """Save one play; a None `played_at` means the current moment."""

    @abstractmethod
    def entries(self) -> list[HistoryEntry]:
        """Every saved play, newest first."""

    @abstractmethod
    def clear(self) -> None:
        """Delete every saved play."""

    def close(self) -> None:
        """Release resources; the default backend has nothing to release."""

    def describe(self) -> str:
        """Short text saying where the history is stored."""
        return self.label
