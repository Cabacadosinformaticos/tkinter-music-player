# Text history backend: one line per play in a UTF-8 file, easy to read and edit
# by hand. Used when the user picks the "text" history in the settings.

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from .base import HistoryBackend, HistoryEntry


def _clean_title(title: str) -> str:
    """Replace tabs and line breaks so a title never breaks the line format."""
    return str(title).replace("\t", " ").replace("\r", " ").replace("\n", " ")


class TextHistory(HistoryBackend):
    """Play history stored as one text line per play."""

    name = "text"
    label = "Text file"

    def __init__(self, path: Path) -> None:
        """Keep the history file path and make sure its folder exists."""
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def record(
        self, title: str, played_at: datetime | None = None, duration: float = 0.0
    ) -> None:
        """Append one play as "played_at<TAB>duration<TAB>title"."""
        if played_at is None:
            played_at = datetime.now()
        line = f"{played_at.isoformat()}\t{float(duration)}\t{_clean_title(title)}\n"
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(line)

    def entries(self) -> list[HistoryEntry]:
        """Read every valid line, newest first; malformed lines are skipped."""
        try:
            with self.path.open("r", encoding="utf-8") as handle:
                lines = handle.readlines()
        except FileNotFoundError:
            return []
        result = []
        for line in lines:
            parsed = self._parse(line)
            if parsed is not None:
                result.append(parsed)
        # Newest first; reversing before the stable sort leaves the last written
        # line first when two plays share the same timestamp.
        result.reverse()
        result.sort(key=lambda item: item.played_at, reverse=True)
        return result

    @staticmethod
    def _parse(line: str) -> HistoryEntry | None:
        """Turn one line into a HistoryEntry, or None when it is empty or malformed."""
        text = line.rstrip("\r\n")
        if not text.strip():
            return None
        parts = text.split("\t", 2)
        if len(parts) != 3:
            return None
        try:
            played_at = datetime.fromisoformat(parts[0])
            duration = float(parts[1])
        except ValueError:
            return None
        return HistoryEntry(title=parts[2], played_at=played_at, duration=duration)

    def clear(self) -> None:
        """Empty the history file."""
        with self.path.open("w", encoding="utf-8"):
            pass

    def describe(self) -> str:
        """Path of the text file that holds the history."""
        return f"Text file: {self.path}"
