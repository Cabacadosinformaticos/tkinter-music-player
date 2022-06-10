# Audio player: a small wrapper around pygame.mixer.music that keeps the state
# of the current song (playing, paused or stopped) and works out the playback
# position, because pygame.get_pos() restarts at every play() call and does not
# count the time spent paused.

from __future__ import annotations

import os
import time
from collections.abc import Callable
from typing import Any


class PlayerError(Exception):
    """Friendly error raised when the audio device or a file cannot be used."""


class AudioPlayer:
    """Play one audio file at a time, using an object with the pygame.mixer.music API."""

    # Time to wait after play() before get_busy() can be trusted: some systems
    # report False for a short moment right after playback starts.
    START_GRACE = 0.3

    def __init__(self, music: Any = None, clock: Callable[[], float] = time.monotonic) -> None:
        self.music = music
        self._clock = clock
        self.state = "stopped"
        self.volume = 1.0
        self._offset = 0.0  # seconds skipped by the last play() call
        self._paused_position = 0.0  # frozen position while paused
        self._played_at = 0.0  # clock value of the last play() or resume()
        if self.music is None:
            self.music = self._open_pygame()

    @staticmethod
    def _open_pygame() -> Any:
        """Import pygame on demand and start the mixer; raise PlayerError when it fails."""
        try:
            import pygame
        except Exception as exc:
            raise PlayerError(f"Audio device not available: pygame is not installed ({exc})") from exc
        try:
            pygame.mixer.init()
        except Exception as exc:
            raise PlayerError(f"Audio device not available: {exc}") from exc
        return pygame.mixer.music

    def play(self, path: str, start: float = 0.0) -> None:
        """Load `path` and start playing from `start` seconds."""
        if not path:
            raise PlayerError("Could not play an empty file name")
        try:
            self.music.load(path)
            self.music.set_volume(self.volume)
            self.music.play(loops=0, start=start)
        except Exception as exc:
            raise PlayerError(f"Could not play {os.path.basename(path)}: {exc}") from exc
        self._offset = float(start)
        self._paused_position = 0.0
        self._played_at = self._clock()
        self.state = "playing"

    def pause(self) -> None:
        """Pause the current song; nothing happens when it is not playing."""
        if self.state != "playing":
            return
        self._paused_position = self._offset + self.music.get_pos() / 1000.0
        self.music.pause()
        self.state = "paused"

    def resume(self) -> None:
        """Continue a paused song; nothing happens when it is not paused."""
        if self.state != "paused":
            return
        self.music.unpause()
        self._played_at = self._clock()
        self.state = "playing"

    def stop(self) -> None:
        """Stop playback and put the position back to the start."""
        self.music.stop()
        self.state = "stopped"
        self._offset = 0.0
        self._paused_position = 0.0

    def seek(self, seconds: float) -> None:
        """Restart the current song at `seconds`, staying paused when it was paused."""
        if self.state == "stopped":
            return
        was_paused = self.state == "paused"
        self.music.play(loops=0, start=seconds)
        self._offset = float(seconds)
        self._played_at = self._clock()
        self.state = "playing"
        if was_paused:
            self.pause()

    def set_volume(self, volume: float) -> None:
        """Set the volume, clamped between 0 and 1, and remember it for the next play()."""
        self.volume = min(1.0, max(0.0, float(volume)))
        self.music.set_volume(self.volume)

    def position(self) -> float:
        """Seconds since the start of the song: start offset plus pygame's counter, frozen while paused."""
        if self.state == "stopped":
            return 0.0
        if self.state == "paused":
            return self._paused_position
        return self._offset + self.music.get_pos() / 1000.0

    def finished(self) -> bool:
        """True exactly once, when a playing song ended by itself; the state then becomes stopped."""
        if self.state != "playing":
            return False
        if self.music.get_busy():
            return False
        if self._clock() - self._played_at < self.START_GRACE:
            return False
        self.state = "stopped"
        self._offset = 0.0
        self._paused_position = 0.0
        return True
