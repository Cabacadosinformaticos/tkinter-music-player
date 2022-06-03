# Playlist model: the Track dataclass, the duration formatter and the Playlist
# class that keeps the list of songs, the current position, the repeat mode,
# the shuffle order and the search filter.

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
        """Create an empty playlist; `rng` feeds the shuffled order."""
        self._rng = rng if rng is not None else random.Random()
        self._order: list[int] | None = None
        self._shuffle = False
        self.tracks: list[Track] = []
        self.current: int = -1
        self.repeat: str = "off"

    @property
    def shuffle(self) -> bool:
        """True when the songs play in a shuffled order instead of the list order."""
        return self._shuffle

    @shuffle.setter
    def shuffle(self, value: bool) -> None:
        """Switch shuffle on or off and drop the old order so a fresh one is built when needed."""
        self._shuffle = bool(value)
        self._order = None

    def __len__(self) -> int:
        """Number of songs in the playlist."""
        return len(self.tracks)

    def __getitem__(self, index: int) -> Track:
        """Song at `index`, with the usual Python indexing rules."""
        return self.tracks[index]

    def _valid_index(self, index: int) -> int | None:
        """Return `index` when it is inside the list, otherwise None; negative indices are invalid."""
        if 0 <= index < len(self.tracks):
            return index
        return None

    def add(self, track: Track) -> int:
        """Append one song and return its index."""
        self.tracks.append(track)
        self._order = None
        return len(self.tracks) - 1

    def add_many(self, tracks: list[Track]) -> None:
        """Append several songs at once, keeping their order."""
        self.tracks.extend(tracks)
        self._order = None

    def remove(self, index: int) -> None:
        """Delete one song, keeping `current` on the same track; an invalid index raises IndexError."""
        real = self._valid_index(index)
        if real is None:
            raise IndexError("playlist index out of range")
        del self.tracks[real]
        self._order = None
        if real < self.current:
            self.current -= 1
        elif real == self.current:
            self.current = -1

    def clear(self) -> None:
        """Remove every song and leave no current track."""
        self.tracks.clear()
        self.current = -1
        self._order = None

    def current_track(self) -> Track | None:
        """Song currently selected, or None when there is none."""
        if 0 <= self.current < len(self.tracks):
            return self.tracks[self.current]
        return None

    def select(self, index: int) -> Track | None:
        """Make the song at `index` current; an invalid index returns None and changes nothing."""
        real = self._valid_index(index)
        if real is None:
            return None
        self.current = real
        self._order = None
        return self.tracks[real]

    def _ensure_order(self) -> list[int]:
        """Return the shuffled order, building it when missing: every index once, the current one first."""
        if self._order is not None:
            return self._order
        order = list(range(len(self.tracks)))
        self._rng.shuffle(order)
        if 0 <= self.current < len(self.tracks):
            order.remove(self.current)
            order.insert(0, self.current)
        self._order = order
        return order

    def _new_cycle(self, previous: int | None) -> int:
        """Build a fresh shuffled order and return its first index, kept away from `previous` when possible."""
        order = list(range(len(self.tracks)))
        self._rng.shuffle(order)
        if previous is not None and len(order) > 1 and order[0] == previous:
            other = self._rng.randrange(1, len(order))
            order[0], order[other] = order[other], order[0]
        self._order = order
        return order[0]

    def _next_index(self) -> int | None:
        """Index of the song after the current one, or None at the end; follows the shuffle order when on."""
        if self.shuffle:
            order = self._ensure_order()
            position = order.index(self.current)
            if position + 1 < len(order):
                return order[position + 1]
            return None
        if self.current + 1 < len(self.tracks):
            return self.current + 1
        return None

    def _previous_index(self) -> int | None:
        """Index of the song before the current one, or None at the start; follows the shuffle order when on."""
        if self.shuffle:
            order = self._ensure_order()
            position = order.index(self.current)
            if position > 0:
                return order[position - 1]
            return None
        if self.current > 0:
            return self.current - 1
        return None

    def advance(self, auto: bool = False) -> int | None:
        """Move to the next song and return its index, or None at the end; `auto` means the song ended by itself."""
        if not self.tracks:
            return None
        if self.current < 0:
            # First play: the first song of the list, or the first of the shuffle order.
            self.current = self._ensure_order()[0] if self.shuffle else 0
            return self.current
        if auto and self.repeat == "one":
            return self.current
        following = self._next_index()
        if following is not None:
            self.current = following
            return following
        # End of the order: repeat "all" wraps, and repeat "one" wraps when the user pressed next.
        if self.repeat == "all" or (self.repeat == "one" and not auto):
            if self.shuffle:
                self.current = self._new_cycle(self.current)
            else:
                self.current = 0
            return self.current
        return None

    def previous(self) -> int | None:
        """Move to the previous song and return its index, or None when the playlist is empty."""
        if not self.tracks:
            return None
        if self.current < 0:
            self.current = self._ensure_order()[0] if self.shuffle else 0
            return self.current
        before = self._previous_index()
        if before is None:
            # First song of the order: repeat "all" wraps to the last one, otherwise restart the first.
            if self.repeat == "all":
                before = self._ensure_order()[-1] if self.shuffle else len(self.tracks) - 1
            else:
                before = self.current
        self.current = before
        return before

    def total_duration(self) -> float:
        """Total length of the playlist in seconds."""
        return sum(track.duration for track in self.tracks)

    def filter(self, query: str) -> list[int]:
        """Indices of the songs whose "title artist album" holds every word of the query, case-insensitive."""
        words = query.lower().split()
        if not words:
            return list(range(len(self.tracks)))
        found = []
        for index, track in enumerate(self.tracks):
            text = f"{track.title} {track.artist} {track.album}".lower()
            if all(word in text for word in words):
                found.append(index)
        return found
