# Tests for the audio player: play, pause, resume, stop, seek, position math,
# volume clamping, the finished() guard and the PlayerError cases.
# A FakeMusic object replaces pygame.mixer.music and a fake clock replaces
# time.monotonic, so the tests never need an audio device or pygame.

from __future__ import annotations

import sys
import types

import pytest

from music_player.player import AudioPlayer, PlayerError


class FakePygameError(Exception):
    """Stands in for pygame.error, which the player has to convert."""


class FakeMusic:
    """Minimal replacement for pygame.mixer.music that records the calls made to it."""

    def __init__(self) -> None:
        self.calls: list[tuple] = []
        self.volume = 1.0
        self.busy = False
        self.pos_ms = 0
        self.path = None
        self.fail_on_load = False

    def load(self, path: str) -> None:
        self.calls.append(("load", path))
        if self.fail_on_load:
            raise FakePygameError("no codec for this file")
        self.path = path
        self.pos_ms = 0
        self.busy = False

    def play(self, loops: int = 0, start: float = 0.0) -> None:
        self.calls.append(("play", start))
        self.pos_ms = 0
        self.busy = True

    def pause(self) -> None:
        self.calls.append(("pause",))
        self.busy = False

    def unpause(self) -> None:
        self.calls.append(("unpause",))
        self.busy = True

    def stop(self) -> None:
        self.calls.append(("stop",))
        self.pos_ms = 0
        self.busy = False

    def set_volume(self, volume: float) -> None:
        self.calls.append(("set_volume", volume))
        self.volume = volume

    def get_busy(self) -> bool:
        return self.busy

    def get_pos(self) -> int:
        return self.pos_ms


class FakeClock:
    """Clock the test moves by hand, used instead of time.monotonic."""

    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


@pytest.fixture
def music() -> FakeMusic:
    return FakeMusic()


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def player(music: FakeMusic, clock: FakeClock) -> AudioPlayer:
    return AudioPlayer(music=music, clock=clock)


def test_with_fake_music_pygame_is_not_needed(monkeypatch):
    monkeypatch.setitem(sys.modules, "pygame", None)
    player = AudioPlayer(music=FakeMusic())
    assert player.state == "stopped"


def test_missing_pygame_gives_player_error(monkeypatch):
    monkeypatch.setitem(sys.modules, "pygame", None)
    with pytest.raises(PlayerError, match="Audio device not available"):
        AudioPlayer()


def test_mixer_init_failure_gives_player_error(monkeypatch):
    """A pygame whose mixer.init() fails (no sound card) becomes a friendly PlayerError."""

    class FakeMixer:
        @staticmethod
        def init() -> None:
            raise FakePygameError("no audio device found")

    fake_pygame = types.ModuleType("pygame")
    fake_pygame.mixer = FakeMixer
    fake_pygame.error = FakePygameError
    monkeypatch.setitem(sys.modules, "pygame", fake_pygame)

    with pytest.raises(PlayerError, match="Audio device not available"):
        AudioPlayer()


def test_play_loads_and_starts_the_song(player: AudioPlayer, music: FakeMusic):
    player.play("C:/music/song.mp3")
    assert player.state == "playing"
    assert music.calls == [("load", "C:/music/song.mp3"), ("set_volume", 1.0), ("play", 0.0)]


def test_position_adds_get_pos_without_offset(player: AudioPlayer, music: FakeMusic):
    player.play("song.mp3")
    music.pos_ms = 1500
    assert player.position() == pytest.approx(1.5)


def test_position_adds_the_start_offset(player: AudioPlayer, music: FakeMusic):
    player.play("song.mp3", start=30.0)
    music.pos_ms = 1000
    assert player.position() == pytest.approx(31.0)


def test_position_is_frozen_while_paused(player: AudioPlayer, music: FakeMusic):
    player.play("song.mp3")
    music.pos_ms = 2000
    player.pause()
    music.pos_ms = 9999  # pygame would not move while paused, the fake is pushed on purpose
    assert player.position() == pytest.approx(2.0)
    assert player.state == "paused"


def test_position_continues_after_resume(player: AudioPlayer, music: FakeMusic):
    player.play("song.mp3")
    music.pos_ms = 2000
    player.pause()
    player.resume()
    music.pos_ms = 2500
    assert player.state == "playing"
    assert ("unpause",) in music.calls
    assert player.position() == pytest.approx(2.5)


def test_position_is_zero_when_stopped(player: AudioPlayer, music: FakeMusic):
    player.play("song.mp3")
    music.pos_ms = 3000
    player.stop()
    assert player.state == "stopped"
    assert player.position() == 0.0


def test_pause_and_resume_do_nothing_when_stopped(player: AudioPlayer, music: FakeMusic):
    player.pause()
    player.resume()
    assert player.state == "stopped"
    assert music.calls == []


def test_seek_restarts_at_the_new_position(player: AudioPlayer, music: FakeMusic):
    player.play("song.mp3")
    music.pos_ms = 5000
    player.seek(10.0)
    assert music.calls[-1] == ("play", 10.0)
    assert player.state == "playing"
    music.pos_ms = 250
    assert player.position() == pytest.approx(10.25)


def test_seek_while_paused_stays_paused(player: AudioPlayer, music: FakeMusic):
    player.play("song.mp3")
    player.pause()
    player.seek(42.0)
    assert player.state == "paused"
    assert music.calls[-1] == ("pause",)
    assert player.position() == pytest.approx(42.0)


def test_seek_while_stopped_does_nothing(player: AudioPlayer, music: FakeMusic):
    player.seek(10.0)
    assert music.calls == []
    assert player.state == "stopped"


def test_finished_becomes_true_once(player: AudioPlayer, music: FakeMusic, clock: FakeClock):
    player.play("song.mp3")
    clock.advance(0.5)
    music.busy = False  # the song reached its end
    assert player.finished() is True
    assert player.state == "stopped"
    assert player.position() == 0.0
    assert player.finished() is False


def test_finished_is_false_right_after_play(player: AudioPlayer, music: FakeMusic):
    player.play("song.mp3")
    music.busy = False  # some systems report this for a moment after play()
    assert player.finished() is False
    assert player.state == "playing"


def test_finished_is_false_while_the_song_is_not_over(player: AudioPlayer, music: FakeMusic, clock: FakeClock):
    player.play("song.mp3")
    clock.advance(5.0)
    assert player.finished() is False
    assert player.state == "playing"


def test_finished_is_false_while_paused(player: AudioPlayer, music: FakeMusic, clock: FakeClock):
    player.play("song.mp3")
    clock.advance(1.0)
    player.pause()
    assert player.finished() is False
    assert player.state == "paused"


def test_volume_is_clamped(player: AudioPlayer, music: FakeMusic):
    player.set_volume(1.5)
    assert player.volume == 1.0
    assert music.volume == 1.0
    player.set_volume(-0.5)
    assert player.volume == 0.0
    assert music.volume == 0.0
    player.set_volume(0.4)
    assert player.volume == pytest.approx(0.4)


def test_volume_is_kept_on_the_next_play(player: AudioPlayer, music: FakeMusic):
    player.set_volume(0.4)
    player.play("song.mp3")
    assert player.volume == pytest.approx(0.4)
    assert music.volume == pytest.approx(0.4)
    assert ("set_volume", pytest.approx(0.4)) in music.calls


def test_play_failure_raises_player_error(player: AudioPlayer, music: FakeMusic):
    music.fail_on_load = True
    with pytest.raises(PlayerError, match="Could not play song.mp3: no codec for this file"):
        player.play("C:/music/song.mp3")
    assert player.state == "stopped"


def test_play_of_an_empty_path_raises_player_error(player: AudioPlayer, music: FakeMusic):
    with pytest.raises(PlayerError, match="empty file name"):
        player.play("")
    assert music.calls == []
