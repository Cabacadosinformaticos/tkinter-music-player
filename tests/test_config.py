# Tests for the configuration module: repository paths, defaults and JSON settings.

from __future__ import annotations

import json
import os

import pytest

from music_player import config


def test_module_paths_point_inside_the_repository():
    assert (config.BASE_DIR / "src" / "music_player").is_dir()
    assert config.ASSETS_DIR == config.BASE_DIR / "assets"
    assert config.IMAGES_DIR == config.ASSETS_DIR / "images"
    assert config.MUSIC_DIR == config.BASE_DIR / "music"
    assert config.DB_CONFIG_FILE == config.BASE_DIR / "db_config.ini"


def test_defaults_when_file_missing(tmp_path):
    settings = config.Settings.load(tmp_path / "settings.json")
    assert settings.values == config.DEFAULTS
    assert settings.values is not config.DEFAULTS


def test_round_trip_save_and_load(tmp_path):
    path = tmp_path / "settings.json"
    settings = config.Settings(path)
    settings["theme"] = "light"
    settings["volume"] = 0.5
    settings["muted"] = True
    settings["last_playlist"] = ["a.mp3", "b.mp3"]
    settings.save()

    loaded = config.Settings.load(path)
    assert loaded["theme"] == "light"
    assert loaded["volume"] == 0.5
    assert loaded["muted"] is True
    assert loaded["last_playlist"] == ["a.mp3", "b.mp3"]


def test_corrupt_json_gives_defaults(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text("{ this is not json", encoding="utf-8")
    assert config.Settings.load(path).values == config.DEFAULTS


def test_json_that_is_not_an_object_gives_defaults(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text("[1, 2, 3]", encoding="utf-8")
    assert config.Settings.load(path).values == config.DEFAULTS


def test_unknown_keys_are_dropped(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"theme": "light", "unknown": 1}), encoding="utf-8")
    settings = config.Settings.load(path)
    assert settings["theme"] == "light"
    assert "unknown" not in settings.values


def test_invalid_values_fall_back_or_clamp(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text(
        json.dumps(
            {
                "theme": "pink",
                "repeat": "x",
                "volume": 5,
                "history_backend": "mongo",
            }
        ),
        encoding="utf-8",
    )
    settings = config.Settings.load(path)
    assert settings["theme"] == "dark"
    assert settings["repeat"] == "off"
    assert settings["volume"] == 1.0
    assert settings["history_backend"] == "sqlite"


def test_volume_wrong_type_falls_back(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"volume": "loud"}), encoding="utf-8")
    assert config.Settings.load(path)["volume"] == 0.8


def test_other_wrong_types_fall_back(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text(
        json.dumps(
            {
                "muted": "yes",
                "shuffle": 1,
                "last_playlist": "song.mp3",
                "last_index": "first",
                "music_dir": 12,
                "window_geometry": None,
            }
        ),
        encoding="utf-8",
    )
    settings = config.Settings.load(path)
    assert settings["muted"] is False
    assert settings["shuffle"] is False
    assert settings["last_playlist"] == []
    assert settings["last_index"] == -1
    assert settings["music_dir"] == config.DEFAULTS["music_dir"]
    assert settings["window_geometry"] == ""


def test_setitem_unknown_key_raises_key_error(tmp_path):
    settings = config.Settings(tmp_path / "settings.json")
    with pytest.raises(KeyError):
        settings["nope"] = 1


def test_setitem_invalid_values_raise_value_error(tmp_path):
    settings = config.Settings(tmp_path / "settings.json")
    cases = [
        ("theme", "pink"),
        ("repeat", "x"),
        ("history_backend", "mongo"),
        ("volume", "loud"),
        ("volume", 5),
        ("muted", "yes"),
    ]
    for key, value in cases:
        with pytest.raises(ValueError):
            settings[key] = value
    # nothing was changed by the failed writes
    assert settings.values == config.DEFAULTS


def test_setitem_accepts_valid_values_and_get_returns_default(tmp_path):
    settings = config.Settings(tmp_path / "settings.json")
    settings["volume"] = 0
    assert settings["volume"] == 0.0
    settings["last_index"] = 3
    assert settings["last_index"] == 3
    assert settings.get("nope", "fallback") == "fallback"


def test_save_is_atomic_and_leaves_no_temp_file(tmp_path):
    path = tmp_path / "settings.json"
    config.Settings(path).save()
    assert path.is_file()
    assert list(tmp_path.glob("*.tmp")) == []

    settings = config.Settings(path)
    settings["theme"] = "light"
    settings.save()
    assert list(tmp_path.glob("*.tmp")) == []
    assert json.loads(path.read_text(encoding="utf-8"))["theme"] == "light"


def test_save_propagates_oserror_and_leaves_no_temp_file(tmp_path, monkeypatch):
    """When os.replace fails the OSError reaches the caller and the temporary file is removed."""
    path = tmp_path / "settings.json"

    def fail_replace(source, target):
        raise OSError("disk full")

    monkeypatch.setattr(os, "replace", fail_replace)

    with pytest.raises(OSError):
        config.Settings(path).save()

    assert not path.exists()
    assert list(tmp_path.glob("*.tmp")) == []


def test_data_dir_honours_environment_and_creates_folder(tmp_path, monkeypatch):
    target = tmp_path / "custom" / "nested"
    monkeypatch.setenv("MUSIC_PLAYER_DATA", str(target))
    assert not target.exists()
    result = config.data_dir()
    assert result == target
    assert result.is_dir()


def test_default_settings_path_uses_data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("MUSIC_PLAYER_DATA", str(tmp_path))
    settings = config.Settings()
    assert settings.path == tmp_path / "settings.json"
