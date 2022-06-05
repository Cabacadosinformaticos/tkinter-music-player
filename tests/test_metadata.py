# Tests for the metadata module: reading tags (title, artist, album, duration)
# and the embedded cover from files made on the fly, and the fallbacks when a
# file has no tags or cannot be read.

from __future__ import annotations

import wave
from io import BytesIO

import pytest
from mutagen.id3 import APIC, TALB, TPE1, TIT2
from mutagen.wave import WAVE
from PIL import Image

from music_player.metadata import read_cover, read_track


def make_wav(path, seconds: float = 0.2) -> None:
    """Write a small WAV file with silence, long enough for a known duration."""
    rate = 8000
    frames = int(rate * seconds)
    with wave.open(str(path), "w") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(b"\x00\x00" * frames)


def make_png() -> bytes:
    """A tiny PNG image in memory, used as the cover art."""
    buffer = BytesIO()
    Image.new("RGB", (4, 4), (200, 40, 40)).save(buffer, format="PNG")
    return buffer.getvalue()


def test_read_track_tags(tmp_path):
    """The four ID3 frames are read back and the WAV duration is about 0.2 seconds."""
    path = tmp_path / "tagged.wav"
    make_wav(path)
    audio = WAVE(str(path))
    audio.add_tags()
    audio.tags.add(TIT2(encoding=3, text="My Song"))
    audio.tags.add(TPE1(encoding=3, text="My Band"))
    audio.tags.add(TALB(encoding=3, text="My Album"))
    audio.save()

    track = read_track(str(path))

    assert track.title == "My Song"
    assert track.artist == "My Band"
    assert track.album == "My Album"
    assert track.duration == pytest.approx(0.2, abs=0.02)
    assert track.path == str(path)


def test_read_cover_returns_png(tmp_path):
    """The bytes stored in the APIC frame come back unchanged."""
    path = tmp_path / "cover.wav"
    make_wav(path)
    png = make_png()
    audio = WAVE(str(path))
    audio.add_tags()
    audio.tags.add(APIC(encoding=3, mime="image/png", type=3, desc="Cover", data=png))
    audio.save()

    assert read_cover(str(path)) == png


def test_read_cover_without_picture_is_none(tmp_path):
    """A file with tags but no picture gives None."""
    path = tmp_path / "nopicture.wav"
    make_wav(path)
    audio = WAVE(str(path))
    audio.add_tags()
    audio.tags.add(TIT2(encoding=3, text="Song"))
    audio.save()

    assert read_cover(str(path)) is None


def test_read_track_without_tags_uses_stem(tmp_path):
    """A file with no tags keeps the file stem as the title and reads the duration."""
    path = tmp_path / "plain_song.wav"
    make_wav(path)

    track = read_track(str(path))

    assert track.title == "plain_song"
    assert track.artist == ""
    assert track.album == ""
    assert track.duration == pytest.approx(0.2, abs=0.02)


def test_read_track_missing_file(tmp_path):
    """A missing file does not raise: the stem is the title and the duration is 0.0."""
    path = tmp_path / "ghost.mp3"

    track = read_track(str(path))

    assert track.title == "ghost"
    assert track.duration == 0.0
    assert read_cover(str(path)) is None


def test_read_track_broken_file(tmp_path):
    """A text file renamed .mp3 does not raise either and gives the safe fallback."""
    path = tmp_path / "fake.mp3"
    path.write_text("this is not audio at all", encoding="utf-8")

    track = read_track(str(path))

    assert track.title == "fake"
    assert track.artist == ""
    assert track.duration == 0.0
    assert read_cover(str(path)) is None
