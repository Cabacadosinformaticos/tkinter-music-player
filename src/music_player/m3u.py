# M3U playlist files: writes the usual "#EXTM3U" list with "#EXTINF" lines and
# reads it back in a tolerant way (BOM, CRLF, comments, missing tags).

from __future__ import annotations

import os

from music_player.playlist import Track


def _file_path(folder: str, track_path: str) -> str:
    """Path of one song relative to the playlist folder with forward slashes; absolute when relpath fails."""
    absolute = os.path.abspath(track_path)
    try:
        relative = os.path.relpath(absolute, folder)
    except ValueError:
        # Different drives on Windows: there is no relative path.
        return absolute.replace("\\", "/")
    return relative.replace("\\", "/")


def save_m3u(path: str, tracks: list[Track]) -> None:
    """Write the playlist as UTF-8: one EXTINF line and one path line per song."""
    folder = os.path.dirname(os.path.abspath(path))
    lines = ["#EXTM3U"]
    for track in tracks:
        seconds = int(track.duration or 0)
        lines.append(f"#EXTINF:{seconds},{track.display_name}")
        lines.append(_file_path(folder, track.path))
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(lines) + "\n")


def _parse_extinf(line: str) -> tuple[float, str | None]:
    """Read the duration and the display name from an "#EXTINF" line; missing or bad values become 0.0 and None."""
    body = line[len("#EXTINF"):].lstrip(":").strip()
    name: str | None = None
    if "," in body:
        body, name = body.split(",", 1)
        name = name.strip() or None
    duration = 0.0
    try:
        duration = float(body.strip())
    except ValueError:
        duration = 0.0
    return duration, name


def _split_name(display: str) -> tuple[str, str]:
    """Split an "Artist - Title" name; without the separator the whole text is the title."""
    if " - " in display:
        artist, title = display.split(" - ", 1)
        return artist.strip(), title.strip()
    return "", display.strip()


def _make_track(folder: str, raw_path: str, display: str | None, duration: float) -> Track:
    """Build one track from a path line, using the EXTINF name when it exists."""
    full = raw_path.replace("/", os.sep)
    if not os.path.isabs(full):
        full = os.path.join(folder, full)
    path = os.path.normpath(full)
    if display:
        artist, title = _split_name(display)
        return Track(path=path, title=title, artist=artist, duration=duration)
    fallback = os.path.splitext(os.path.basename(path))[0]
    return Track(path=path, title=fallback, duration=duration)


def load_m3u(path: str) -> list[Track]:
    """Read an M3U file; relative paths are resolved against the playlist folder and files are not checked."""
    folder = os.path.dirname(os.path.abspath(path))
    tracks: list[Track] = []
    display: str | None = None
    duration = 0.0
    # utf-8-sig drops a possible byte order mark at the start of the file.
    with open(path, "r", encoding="utf-8-sig") as handle:
        for raw in handle:
            line = raw.strip()
            if not line:
                continue
            if line.startswith("#EXTINF"):
                duration, display = _parse_extinf(line)
                continue
            if line.startswith("#"):
                continue
            tracks.append(_make_track(folder, line, display, duration))
            display = None
            duration = 0.0
    return tracks
