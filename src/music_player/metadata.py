# Metadata reader: reads the title, artist, album and duration of an audio
# file and its embedded cover picture, using mutagen and never raising.

from __future__ import annotations

import os

from mutagen import File as MutagenFile

from music_player.playlist import Track

# Tag names per field: ID3 frames, MP4 atoms and the usual Vorbis comment keys.
_TITLE_KEYS = ("TIT2", "\xa9nam", "title")
_ARTIST_KEYS = ("TPE1", "\xa9ART", "artist")
_ALBUM_KEYS = ("TALB", "\xa9alb", "album")


def _frame_text(value) -> str | None:
    """Text inside one tag value: ID3 frames hold a list in `.text`, other formats a string or list."""
    text = getattr(value, "text", None)
    if text:
        return str(text[0])
    if isinstance(value, (list, tuple)) and value:
        return str(value[0])
    if isinstance(value, str) and value:
        return value
    return None


def _lookup(tags, keys: tuple[str, ...]) -> str | None:
    """First readable value among `keys`, or None when none of them is present."""
    if tags is None:
        return None
    for key in keys:
        try:
            value = tags.get(key)
        except Exception:
            value = None
        if value is None:
            continue
        text = _frame_text(value)
        if text:
            return text
    return None


def read_track(path: str) -> Track:
    """Read the tags of one file; on any problem the title is the file stem and the duration 0.0."""
    fallback = os.path.splitext(os.path.basename(os.fspath(path)))[0]
    title = fallback
    artist = ""
    album = ""
    duration = 0.0
    try:
        audio = MutagenFile(os.fspath(path))
        if audio is not None:
            tags = getattr(audio, "tags", None)
            title = _lookup(tags, _TITLE_KEYS) or fallback
            artist = _lookup(tags, _ARTIST_KEYS) or ""
            album = _lookup(tags, _ALBUM_KEYS) or ""
            info = getattr(audio, "info", None)
            length = getattr(info, "length", None)
            if length:
                duration = float(length)
    except Exception:
        # A missing, unreadable or tagless file still gives a usable track.
        pass
    return Track(path=os.fspath(path), title=title, artist=artist, album=album, duration=duration)


def _picture_in_tags(tags) -> bytes | None:
    """First picture found in ID3 APIC frames or in the MP4 "covr" tag."""
    if tags is None:
        return None
    try:
        keys = list(tags.keys())
    except Exception:
        return None
    # ID3 APIC frames; a described picture has a key like "APIC:cover".
    for key in keys:
        if not isinstance(key, str):
            continue
        upper = key.upper()
        if upper == "APIC" or upper.startswith("APIC:"):
            data = getattr(tags[key], "data", None)
            if data:
                return bytes(data)
    # MP4 cover art, stored as a list of bytes.
    try:
        covers = tags.get("covr")
    except Exception:
        covers = None
    if covers:
        try:
            return bytes(covers[0])
        except Exception:
            return None
    return None


def read_cover(path: str) -> bytes | None:
    """Embedded cover picture bytes (ID3 APIC, FLAC picture or MP4 covr), or None when there is none."""
    try:
        audio = MutagenFile(os.fspath(path))
        if audio is None:
            return None
        picture = _picture_in_tags(getattr(audio, "tags", None))
        if picture:
            return picture
        # FLAC keeps its pictures outside the comments.
        pictures = getattr(audio, "pictures", None)
        if pictures:
            return bytes(pictures[0].data)
    except Exception:
        return None
    return None
