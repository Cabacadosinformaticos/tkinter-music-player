# Playlist model: the Track dataclass, the duration formatter and the Playlist
# class that keeps the list of songs, the current position and the repeat mode.

from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass
class Track:
    """One song: the file path and the tags shown in the interface."""

    path: str
    title: str
    artist: str = ""
    album: str = ""
    duration: float = 0.0

    @property
    def display_name(self) -> str:
        """Text for the song: "Artist - Title" when there is an artist, else the title."""
        if self.artist:
            return f"{self.artist} - {self.title}"
        return self.title


def format_duration(seconds: float | None) -> str:
    """Format seconds as "m:ss", or "h:mm:ss" from one hour on; negative or None gives "0:00"."""
    if seconds is None or seconds < 0:
        return "0:00"
    total = int(seconds)
    hours, rest = divmod(total, 3600)
    minutes, secs = divmod(rest, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


class Playlist:
    """Ordered list of tracks with a current position, a repeat mode and a shuffle flag."""

    def __init__(self, rng: random.Random | None = None) -> None:
        """Create an empty playlist; `rng` is kept for the shuffle order of a later task."""
        self._rng = rng if rng is not None else random.Random()
        self.tracks: list[Track] = []
        self.current: int = -1
        self.repeat: str = "off"
        self.shuffle: bool = False

    def __len__(self) -> int:
        """Number of songs in the playlist."""
        return len(self.tracks)

    def __getitem__(self, index: int) -> Track:
        """Song at `index`, with the usual Python indexing rules."""
        return self.tracks[index]

    def _index_or_none(self, index: int) -> int | None:
        """Turn a possibly negative index into a real one, or None when it is out of range."""
        if index < 0:
            index += len(self.tracks)
        if 0 <= index < len(self.tracks):
            return index
        return None

    def add(self, track: Track) -> int:
        """Append one song and return its index."""
        self.tracks.append(track)
        return len(self.tracks) - 1

    def add_many(self, tracks: list[Track]) -> None:
        """Append several songs at once, keeping their order."""
        self.tracks.extend(tracks)

    def remove(self, index: int) -> None:
        """Delete one song, keeping `current` on the same track; an invalid index raises IndexError."""
        real = self._index_or_none(index)
        if real is None:
            raise IndexError("playlist index out of range")
        del self.tracks[real]
        if real < self.current:
            self.current -= 1
        elif real == self.current:
            self.current = -1

    def clear(self) -> None:
        """Remove every song and leave no current track."""
        self.tracks.clear()
        self.current = -1

    def current_track(self) -> Track | None:
        """Song currently selected, or None when there is none."""
        if 0 <= self.current < len(self.tracks):
            return self.tracks[self.current]
        return None

    def select(self, index: int) -> Track | None:
        """Make the song at `index` current; an invalid index returns None and changes nothing."""
        real = self._index_or_none(index)
        if real is None:
            return None
        self.current = real
        return self.tracks[real]

    def _next_index(self) -> int | None:
        """Index of the song after the current one, or None at the end; the shuffle order plugs in here."""
        if self.current + 1 < len(self.tracks):
            return self.current + 1
        return None

    def _previous_index(self) -> int | None:
        """Index of the song before the current one, or None at the start; the shuffle order plugs in here."""
        if self.current > 0:
            return self.current - 1
        return None

    def advance(self, auto: bool = False) -> int | None:
        """Move to the next song and return its index, or None at the end; `auto` means the song ended by itself."""
        if not self.tracks:
            return None
        if self.current < 0:
            self.current = 0
            return 0
        if auto and self.repeat == "one":
            return self.current
        following = self._next_index()
        if following is not None:
            self.current = following
            return following
        # End of the list: repeat "all" wraps, and repeat "one" wraps when the user pressed next.
        if self.repeat == "all" or (self.repeat == "one" and not auto):
            self.current = 0
            return 0
        return None

    def previous(self) -> int | None:
        """Move to the previous song and return its index, or None when the playlist is empty."""
        if not self.tracks:
            return None
        if self.current < 0:
            self.current = 0
            return 0
        before = self._previous_index()
        if before is None:
            # First song: repeat "all" wraps to the last one, otherwise restart the first.
            if self.repeat == "all":
                before = len(self.tracks) - 1
            else:
                before = self.current
        self.current = before
        return before

    def total_duration(self) -> float:
        """Total length of the playlist in seconds."""
        return sum(track.duration for track in self.tracks)
