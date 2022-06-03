# Tests for the playlist module: Track, format_duration and the Playlist class
# (add and remove, current tracking, advance, previous, totals, shuffle and filter).

from __future__ import annotations

import random

import pytest

from music_player.playlist import Playlist, Track, format_duration


def make_tracks(*names: str) -> list[Track]:
    """Small helper: build tracks whose title is the given name."""
    return [Track(path=f"{name}.mp3", title=name) for name in names]


# --- format_duration ---

@pytest.mark.parametrize(
    "seconds, expected",
    [
        (0, "0:00"),
        (59, "0:59"),
        (61, "1:01"),
        (3599, "59:59"),
        (3600, "1:00:00"),
        (3725.7, "1:02:05"),
    ],
)
def test_format_duration(seconds, expected):
    assert format_duration(seconds) == expected


def test_format_duration_negative_gives_zero():
    assert format_duration(-1) == "0:00"
    assert format_duration(-0.5) == "0:00"


def test_format_duration_none_gives_zero():
    assert format_duration(None) == "0:00"


def test_format_duration_over_two_hours():
    assert format_duration(7322) == "2:02:02"


# --- Track ---

def test_display_name_without_artist():
    assert Track(path="a.mp3", title="Song").display_name == "Song"


def test_display_name_with_artist():
    track = Track(path="a.mp3", title="Song", artist="Band")
    assert track.display_name == "Band - Song"


def test_track_defaults():
    track = Track(path="a.mp3", title="Song")
    assert track.artist == ""
    assert track.album == ""
    assert track.duration == 0.0


# --- construction and basic access ---

def test_new_playlist_is_empty():
    playlist = Playlist()
    assert len(playlist) == 0
    assert playlist.current == -1
    assert playlist.current_track() is None
    assert playlist.tracks == []
    assert playlist.repeat == "off"
    assert playlist.shuffle is False


def test_rng_is_stored_for_the_shuffle_order():
    rng = random.Random(7)
    assert Playlist(rng)._rng is rng


def test_add_returns_the_index_and_keeps_order():
    playlist = Playlist()
    first = Track(path="a.mp3", title="a")
    second = Track(path="b.mp3", title="b")
    assert playlist.add(first) == 0
    assert playlist.add(second) == 1
    assert len(playlist) == 2
    assert playlist[0] is first
    assert playlist[1] is second


def test_add_many_and_negative_getitem():
    playlist = Playlist()
    playlist.add_many(make_tracks("a", "b", "c"))
    assert len(playlist) == 3
    assert playlist[-1].title == "c"


def test_clear_removes_everything():
    playlist = Playlist()
    playlist.add_many(make_tracks("a", "b"))
    playlist.select(1)
    playlist.clear()
    assert len(playlist) == 0
    assert playlist.tracks == []
    assert playlist.current == -1
    assert playlist.current_track() is None


# --- remove ---

def test_remove_invalid_index_raises():
    playlist = Playlist()
    playlist.add_many(make_tracks("a", "b"))
    with pytest.raises(IndexError):
        playlist.remove(2)
    with pytest.raises(IndexError):
        playlist.remove(-3)
    with pytest.raises(IndexError):
        Playlist().remove(0)


def test_remove_after_current_keeps_current():
    playlist = Playlist()
    playlist.add_many(make_tracks("a", "b", "c"))
    playlist.select(0)
    playlist.remove(2)
    assert playlist.current == 0
    assert playlist.current_track().title == "a"
    assert len(playlist) == 2


def test_remove_before_current_shifts_current_down():
    playlist = Playlist()
    playlist.add_many(make_tracks("a", "b", "c"))
    playlist.select(2)
    playlist.remove(0)
    assert playlist.current == 1
    assert playlist.current_track().title == "c"


def test_remove_current_sets_current_to_minus_one():
    playlist = Playlist()
    playlist.add_many(make_tracks("a", "b", "c"))
    playlist.select(1)
    playlist.remove(1)
    assert playlist.current == -1
    assert playlist.current_track() is None
    assert len(playlist) == 2


def test_remove_with_negative_index_raises():
    playlist = Playlist()
    playlist.add_many(make_tracks("a", "b", "c"))
    playlist.select(2)
    with pytest.raises(IndexError):
        playlist.remove(-1)
    assert len(playlist) == 3
    assert playlist.current == 2


def test_remove_without_current_keeps_minus_one():
    playlist = Playlist()
    playlist.add_many(make_tracks("a", "b"))
    playlist.remove(0)
    assert playlist.current == -1
    assert len(playlist) == 1


# --- select ---

def test_select_sets_current_and_returns_the_track():
    playlist = Playlist()
    playlist.add_many(make_tracks("a", "b", "c"))
    assert playlist.select(2).title == "c"
    assert playlist.current == 2
    assert playlist.current_track().title == "c"


def test_select_negative_index_is_invalid():
    playlist = Playlist()
    playlist.add_many(make_tracks("a", "b", "c"))
    assert playlist.select(0).title == "a"
    assert playlist.select(-1) is None
    assert playlist.current == 0


def test_select_invalid_index_changes_nothing():
    playlist = Playlist()
    playlist.add_many(make_tracks("a", "b"))
    playlist.select(0)
    assert playlist.select(5) is None
    assert playlist.current == 0
    assert playlist.select(-3) is None
    assert playlist.current == 0


# --- advance ---

@pytest.mark.parametrize("repeat", ["off", "all", "one"])
@pytest.mark.parametrize("auto", [False, True])
def test_advance_without_current_starts_at_the_first(repeat, auto):
    playlist = Playlist()
    playlist.add_many(make_tracks("a", "b", "c"))
    playlist.repeat = repeat
    assert playlist.advance(auto) == 0
    assert playlist.current == 0


@pytest.mark.parametrize("repeat", ["off", "all", "one"])
@pytest.mark.parametrize("auto", [False, True])
def test_advance_on_empty_playlist_returns_none(repeat, auto):
    playlist = Playlist()
    playlist.repeat = repeat
    assert playlist.advance(auto) is None
    assert playlist.current == -1


@pytest.mark.parametrize("repeat", ["off", "all"])
@pytest.mark.parametrize("auto", [False, True])
def test_advance_from_the_middle_goes_to_the_next(repeat, auto):
    playlist = Playlist()
    playlist.add_many(make_tracks("a", "b", "c"))
    playlist.select(0)
    playlist.repeat = repeat
    assert playlist.advance(auto) == 1
    assert playlist.current == 1


def test_advance_from_the_middle_with_repeat_one_and_next_goes_to_the_next():
    playlist = Playlist()
    playlist.add_many(make_tracks("a", "b", "c"))
    playlist.select(0)
    playlist.repeat = "one"
    assert playlist.advance(auto=False) == 1
    assert playlist.current == 1


@pytest.mark.parametrize("auto", [False, True])
def test_advance_at_the_end_with_repeat_off_returns_none(auto):
    playlist = Playlist()
    playlist.add_many(make_tracks("a", "b", "c"))
    playlist.select(2)
    playlist.repeat = "off"
    assert playlist.advance(auto) is None
    assert playlist.current == 2


@pytest.mark.parametrize("auto", [False, True])
def test_advance_at_the_end_with_repeat_all_wraps(auto):
    playlist = Playlist()
    playlist.add_many(make_tracks("a", "b", "c"))
    playlist.select(2)
    playlist.repeat = "all"
    assert playlist.advance(auto) == 0
    assert playlist.current == 0


def test_advance_repeat_one_with_auto_repeats_the_same_song():
    playlist = Playlist()
    playlist.add_many(make_tracks("a", "b", "c"))
    playlist.select(1)
    playlist.repeat = "one"
    assert playlist.advance(auto=True) == 1
    assert playlist.current == 1


def test_advance_repeat_one_at_the_end_with_auto_repeats_the_same_song():
    playlist = Playlist()
    playlist.add_many(make_tracks("a", "b", "c"))
    playlist.select(2)
    playlist.repeat = "one"
    assert playlist.advance(auto=True) == 2
    assert playlist.current == 2


def test_advance_repeat_one_at_the_end_with_next_wraps_to_the_first():
    playlist = Playlist()
    playlist.add_many(make_tracks("a", "b", "c"))
    playlist.select(2)
    playlist.repeat = "one"
    assert playlist.advance(auto=False) == 0
    assert playlist.current == 0


def test_advance_with_one_song_and_repeat_off_returns_none():
    playlist = Playlist()
    playlist.add_many(make_tracks("a"))
    playlist.select(0)
    assert playlist.advance(auto=True) is None
    assert playlist.advance(auto=False) is None
    assert playlist.current == 0


@pytest.mark.parametrize("auto", [False, True])
def test_advance_with_one_song_and_repeat_all_wraps_to_it(auto):
    playlist = Playlist()
    playlist.add_many(make_tracks("a"))
    playlist.select(0)
    playlist.repeat = "all"
    assert playlist.advance(auto) == 0
    assert playlist.current == 0


# --- previous ---

def test_previous_on_empty_playlist_returns_none():
    playlist = Playlist()
    assert playlist.previous() is None
    assert playlist.current == -1


def test_previous_without_current_goes_to_the_first():
    playlist = Playlist()
    playlist.add_many(make_tracks("a", "b", "c"))
    assert playlist.previous() == 0
    assert playlist.current == 0


@pytest.mark.parametrize("repeat", ["off", "one"])
def test_previous_at_the_first_stays_on_the_first(repeat):
    playlist = Playlist()
    playlist.add_many(make_tracks("a", "b", "c"))
    playlist.select(0)
    playlist.repeat = repeat
    assert playlist.previous() == 0
    assert playlist.current == 0


def test_previous_at_the_first_with_repeat_all_wraps_to_the_last():
    playlist = Playlist()
    playlist.add_many(make_tracks("a", "b", "c"))
    playlist.select(0)
    playlist.repeat = "all"
    assert playlist.previous() == 2
    assert playlist.current == 2


def test_previous_from_the_middle_goes_back():
    playlist = Playlist()
    playlist.add_many(make_tracks("a", "b", "c"))
    playlist.select(2)
    assert playlist.previous() == 1
    assert playlist.previous() == 0
    assert playlist.current == 0


def test_previous_from_the_last_with_repeat_all_goes_to_the_song_before():
    playlist = Playlist()
    playlist.add_many(make_tracks("a", "b", "c"))
    playlist.select(2)
    playlist.repeat = "all"
    assert playlist.previous() == 1
    assert playlist.current == 1


# --- total_duration ---

def test_total_duration_of_empty_playlist_is_zero():
    assert Playlist().total_duration() == 0


def test_total_duration_sums_every_track():
    playlist = Playlist()
    playlist.add_many(
        [
            Track(path="a.mp3", title="a", duration=10.5),
            Track(path="b.mp3", title="b", duration=0.5),
            Track(path="c.mp3", title="c"),
        ]
    )
    assert playlist.total_duration() == pytest.approx(11.0)


# --- shuffle ---

def shuffled_playlist(*names: str) -> Playlist:
    """Small helper: a shuffled playlist with a fixed random seed, ready to play."""
    playlist = Playlist(random.Random(1))
    playlist.add_many(make_tracks(*names))
    playlist.shuffle = True
    return playlist


def test_shuffle_visits_every_song_once_per_cycle():
    playlist = shuffled_playlist("a", "b", "c", "d", "e")
    visited = [playlist.advance()]
    while True:
        following = playlist.advance()
        if following is None:
            break
        visited.append(following)
        assert len(visited) <= len(playlist)
    assert sorted(visited) == [0, 1, 2, 3, 4]


def test_shuffle_previous_walks_back_through_played_songs():
    playlist = shuffled_playlist("a", "b", "c", "d")
    first = playlist.advance()
    second = playlist.advance()
    third = playlist.advance()
    assert playlist.previous() == second
    assert playlist.previous() == first
    # At the first song of the order it restarts it, as in sequential mode.
    assert playlist.previous() == first
    assert playlist.current == first
    assert third not in (first, second)


def test_shuffle_previous_at_the_first_with_repeat_all_wraps_to_the_last_of_the_order():
    # A first playlist with the same seed reveals the order the second one will use.
    probe = shuffled_playlist("a", "b", "c", "d")
    order = []
    while True:
        following = probe.advance()
        if following is None:
            break
        order.append(following)
    playlist = shuffled_playlist("a", "b", "c", "d")
    playlist.repeat = "all"
    assert playlist.advance() == order[0]
    assert playlist.previous() == order[-1]
    assert playlist.current == order[-1]


def test_shuffle_repeat_all_new_cycle_does_not_repeat_the_last_song():
    playlist = shuffled_playlist("a", "b", "c", "d")
    playlist.repeat = "all"
    last = playlist.advance()
    for _ in range(len(playlist) - 1):
        last = playlist.advance()
    assert playlist.current == last
    first_of_new_cycle = playlist.advance()
    assert first_of_new_cycle != last
    assert 0 <= first_of_new_cycle < len(playlist)


def test_switching_shuffle_off_makes_advance_sequential():
    playlist = shuffled_playlist("a", "b", "c", "d")
    playlist.advance()
    playlist.advance()
    playlist.shuffle = False
    assert playlist.select(0).title == "a"
    assert playlist.advance() == 1
    assert playlist.advance() == 2


def test_switching_shuffle_on_builds_a_new_order_from_the_current_song():
    playlist = Playlist(random.Random(1))
    playlist.add_many(make_tracks("a", "b", "c", "d"))
    playlist.select(2)
    playlist.shuffle = True
    visited = [playlist.current]
    while True:
        following = playlist.advance()
        if following is None:
            break
        visited.append(following)
    assert visited[0] == 2
    assert sorted(visited) == [0, 1, 2, 3]


def test_shuffle_add_and_remove_keep_the_order_valid():
    playlist = shuffled_playlist("a", "b", "c", "d", "e")
    playlist.advance()
    playlist.advance()
    current = playlist.current
    other = (current + 1) % len(playlist)
    playlist.add(Track(path="f.mp3", title="f"))
    playlist.remove(other)
    assert 0 <= playlist.current < len(playlist)
    visited = [playlist.current]
    for _ in range(len(playlist) - 1):
        following = playlist.advance()
        assert following is not None
        assert 0 <= following < len(playlist)
        assert following not in visited
        visited.append(following)
    assert sorted(visited) == list(range(len(playlist)))


def test_shuffle_select_starts_a_new_order_from_the_selected_song():
    playlist = shuffled_playlist("a", "b", "c", "d")
    playlist.advance()
    playlist.select(1)
    visited = [playlist.current]
    while True:
        following = playlist.advance()
        if following is None:
            break
        visited.append(following)
    assert visited[0] == 1
    assert sorted(visited) == [0, 1, 2, 3]


def test_shuffle_with_one_song_and_repeat_all_repeats_it():
    playlist = shuffled_playlist("a")
    playlist.repeat = "all"
    assert playlist.advance() == 0
    assert playlist.advance() == 0
    assert playlist.previous() == 0


def test_shuffle_with_one_song_and_repeat_off_ends():
    playlist = shuffled_playlist("a")
    assert playlist.advance() == 0
    assert playlist.advance() is None
    assert playlist.previous() == 0


def test_shuffle_advance_on_empty_playlist_returns_none():
    playlist = Playlist(random.Random(1))
    playlist.shuffle = True
    assert playlist.advance() is None
    assert playlist.previous() is None
    assert playlist.current == -1


# --- filter ---

def test_filter_with_empty_query_returns_all_indices():
    playlist = Playlist()
    playlist.add_many(make_tracks("a", "b", "c"))
    assert playlist.filter("") == [0, 1, 2]
    assert playlist.filter("   ") == [0, 1, 2]


def test_filter_without_match_returns_empty():
    playlist = Playlist()
    playlist.add_many(make_tracks("a", "b"))
    assert playlist.filter("zzz") == []


def test_filter_is_case_insensitive_and_needs_every_word():
    playlist = Playlist()
    playlist.add_many(
        [
            Track(path="1.mp3", title="Hotel California", artist="Eagles", album="Hotel California"),
            Track(path="2.mp3", title="Take It Easy", artist="Eagles", album="Eagles"),
            Track(path="3.mp3", title="Bohemian Rhapsody", artist="Queen", album="A Night at the Opera"),
        ]
    )
    assert playlist.filter("hotel") == [0]
    assert playlist.filter("HOTEL CALIFORNIA") == [0]
    assert playlist.filter("queen opera") == [2]
    assert playlist.filter("queen hotel") == []


def test_filter_matches_artist_and_album():
    playlist = Playlist()
    playlist.add_many(
        [
            Track(path="1.mp3", title="Song", artist="Eagles", album="Hotel California"),
            Track(path="2.mp3", title="Song", artist="Queen", album="Opera"),
        ]
    )
    assert playlist.filter("eagles") == [0]
    assert playlist.filter("opera") == [1]


# --- negative indices ---

def test_negative_indices_are_invalid_in_select_and_remove():
    playlist = Playlist()
    playlist.add_many(make_tracks("a", "b", "c"))
    playlist.select(2)
    assert playlist.select(-1) is None
    assert playlist.current == 2
    with pytest.raises(IndexError):
        playlist.remove(-1)
    assert len(playlist) == 3
    assert playlist.current == 2
