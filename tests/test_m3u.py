# Tests for the m3u module: saving and loading playlists, relative and absolute
# paths, BOM and CRLF files, plain M3U files, comments, unicode titles and
# malformed EXTINF values.

from __future__ import annotations

import os

from music_player.m3u import load_m3u, save_m3u
from music_player.playlist import Track


def test_round_trip_relative_paths(tmp_path):
    """A written playlist points to the songs relative to its own folder and loads back the same data."""
    folder = tmp_path / "lists"
    folder.mkdir()
    music = tmp_path / "music"
    music.mkdir()
    song = music / "song.mp3"
    song.write_bytes(b"not real audio")
    playlist = folder / "mix.m3u"

    save_m3u(str(playlist), [Track(path=str(song), title="Song", artist="Band", duration=125.0)])

    text = playlist.read_text(encoding="utf-8")
    assert text.startswith("#EXTM3U\n")
    assert "#EXTINF:125,Band - Song" in text
    assert "../music/song.mp3" in text

    loaded = load_m3u(str(playlist))
    assert len(loaded) == 1
    assert loaded[0].title == "Song"
    assert loaded[0].artist == "Band"
    assert loaded[0].duration == 125.0
    assert loaded[0].path == os.path.normpath(str(song))


def test_save_absolute_when_relpath_fails(tmp_path, monkeypatch):
    """When the drive is different os.path.relpath raises and the writer falls back to the absolute path."""
    playlist = tmp_path / "list.m3u"
    song = tmp_path / "song.mp3"

    def raise_value_error(*args, **kwargs):
        raise ValueError("path is on another drive")

    monkeypatch.setattr(os.path, "relpath", raise_value_error)

    save_m3u(str(playlist), [Track(path=str(song), title="Song")])

    text = playlist.read_text(encoding="utf-8")
    assert str(song).replace("\\", "/") in text


def test_load_file_with_bom(tmp_path):
    """A UTF-8 BOM at the start of the file is ignored."""
    playlist = tmp_path / "bom.m3u"
    playlist.write_text("#EXTM3U\n#EXTINF:10,Artist - Title\nsong.mp3\n", encoding="utf-8-sig")

    loaded = load_m3u(str(playlist))

    assert len(loaded) == 1
    assert loaded[0].artist == "Artist"
    assert loaded[0].title == "Title"
    assert loaded[0].duration == 10.0


def test_load_file_with_crlf(tmp_path):
    """A file written with CRLF line endings loads the same way."""
    playlist = tmp_path / "crlf.m3u"
    playlist.write_bytes(b"#EXTM3U\r\n#EXTINF:5,Band - Song\r\nsong.mp3\r\n")

    loaded = load_m3u(str(playlist))

    assert len(loaded) == 1
    assert loaded[0].artist == "Band"
    assert loaded[0].title == "Song"


def test_load_plain_m3u_without_extinf(tmp_path):
    """A plain M3U file with only paths uses the file name without extension as the title."""
    playlist = tmp_path / "plain.m3u"
    playlist.write_text("first.mp3\nsub/second.mp3\n", encoding="utf-8")

    loaded = load_m3u(str(playlist))

    assert [track.title for track in loaded] == ["first", "second"]
    assert [track.artist for track in loaded] == ["", ""]


def test_load_ignores_comments_and_blank_lines(tmp_path):
    """Comment lines and empty lines are skipped."""
    playlist = tmp_path / "comments.m3u"
    playlist.write_text(
        "#EXTM3U\n\n# just a comment\n#EXTINF:7,The Band - The Song\n\nsong.mp3\n\n",
        encoding="utf-8",
    )

    loaded = load_m3u(str(playlist))

    assert len(loaded) == 1
    assert loaded[0].artist == "The Band"
    assert loaded[0].title == "The Song"


def test_load_extinf_with_non_integer_duration(tmp_path):
    """A malformed duration becomes 0.0 and the title is still read."""
    playlist = tmp_path / "bad.m3u"
    playlist.write_text("#EXTM3U\n#EXTINF:not-a-number,Artist - Title\nsong.mp3\n", encoding="utf-8")

    loaded = load_m3u(str(playlist))

    assert loaded[0].duration == 0.0
    assert loaded[0].artist == "Artist"
    assert loaded[0].title == "Title"


def test_load_unicode_titles(tmp_path):
    """Titles and artists with accents survive a save and load round trip."""
    folder = tmp_path / "lists"
    folder.mkdir()
    music = tmp_path / "music"
    music.mkdir()
    song = music / "canção.mp3"
    song.write_bytes(b"x")
    playlist = folder / "unicode.m3u"

    save_m3u(str(playlist), [Track(path=str(song), title="Canção", artist="João", duration=42.0)])
    loaded = load_m3u(str(playlist))

    assert loaded[0].title == "Canção"
    assert loaded[0].artist == "João"


def test_load_resolves_relative_paths_against_folder(tmp_path):
    """A relative path in the file becomes an absolute path based on the playlist folder."""
    folder = tmp_path / "lists"
    folder.mkdir()
    playlist = folder / "sub.m3u"
    playlist.write_text("#EXTM3U\n../music/song.mp3\n", encoding="utf-8")

    loaded = load_m3u(str(playlist))

    expected = os.path.normpath(str(tmp_path / "music" / "song.mp3"))
    assert loaded[0].path == expected
    assert loaded[0].title == "song"


def test_load_absolute_path_stays_absolute(tmp_path):
    """An absolute path in the file is kept as it is."""
    song = tmp_path / "song.mp3"
    playlist = tmp_path / "absolute.m3u"
    playlist.write_text(f"#EXTM3U\n{song}\n", encoding="utf-8")

    loaded = load_m3u(str(playlist))

    assert loaded[0].path == os.path.normpath(str(song))
