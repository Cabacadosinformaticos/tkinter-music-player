# Configuration for the music player: the fixed paths inside the repository and a
# small Settings class that reads and writes the user preferences as a JSON file.

from __future__ import annotations

import copy
import json
import os
import tempfile
from pathlib import Path

# Repository root, two folders above this file (src/music_player/config.py).
BASE_DIR: Path = Path(__file__).resolve().parents[2]

# Folders and files used by the program.
ASSETS_DIR: Path = BASE_DIR / "assets"
IMAGES_DIR: Path = ASSETS_DIR / "images"
MUSIC_DIR: Path = BASE_DIR / "music"
DB_CONFIG_FILE: Path = BASE_DIR / "db_config.ini"

# Available history storage backends.
HISTORY_BACKENDS = ("sqlite", "text", "sqlserver")

# Valid choices for the settings that hold one of a few names.
_THEMES = ("dark", "light")
_REPEATS = ("off", "one", "all")

# Default settings, copied for every new Settings object.
DEFAULTS = {
    "history_backend": "sqlite",
    "theme": "dark",
    "volume": 0.8,
    "muted": False,
    "shuffle": False,
    "repeat": "off",
    "last_playlist": [],
    "last_index": -1,
    "music_dir": str(MUSIC_DIR),
    "window_geometry": "",
}


def data_dir() -> Path:
    """Folder for settings and history; uses MUSIC_PLAYER_DATA when set, created if missing."""
    override = os.environ.get("MUSIC_PLAYER_DATA")
    folder = Path(override) if override else BASE_DIR / "data"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def _is_number(value: object) -> bool:
    """True for int or float values, but not for bool."""
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _validate(key: str, value: object) -> object:
    """Return the value for a known key, or raise ValueError when it does not fit."""
    if key == "history_backend":
        if isinstance(value, str) and value in HISTORY_BACKENDS:
            return value
    elif key == "theme":
        if isinstance(value, str) and value in _THEMES:
            return value
    elif key == "repeat":
        if isinstance(value, str) and value in _REPEATS:
            return value
    elif key == "volume":
        if _is_number(value) and 0.0 <= float(value) <= 1.0:
            return float(value)
    elif key in ("muted", "shuffle"):
        if isinstance(value, bool):
            return value
    elif key == "last_playlist":
        if isinstance(value, list) and all(isinstance(item, str) for item in value):
            return list(value)
    elif key == "last_index":
        if isinstance(value, int) and not isinstance(value, bool):
            return value
    elif key in ("music_dir", "window_geometry"):
        if isinstance(value, str):
            return value
    raise ValueError(f"invalid value for {key!r}: {value!r}")


def _clean(key: str, value: object) -> object:
    """Value read from the file: volume is clamped, anything else falls back to the default."""
    if key == "volume" and _is_number(value):
        return min(1.0, max(0.0, float(value)))
    try:
        return _validate(key, value)
    except ValueError:
        return copy.deepcopy(DEFAULTS[key])


class Settings:
    """User preferences loaded from and saved to a JSON file."""

    def __init__(self, path: Path | None = None) -> None:
        """Start from a copy of the defaults, with an optional custom file path."""
        self.path = Path(path) if path is not None else data_dir() / "settings.json"
        self.values: dict = copy.deepcopy(DEFAULTS)

    @classmethod
    def load(cls, path: Path | None = None) -> Settings:
        """Read the settings file; a missing or corrupt file keeps the defaults."""
        settings = cls(path)
        try:
            with settings.path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, ValueError):
            return settings
        if not isinstance(data, dict):
            return settings
        for key in DEFAULTS:
            if key in data:
                settings.values[key] = _clean(key, data[key])
        return settings

    def __getitem__(self, key: str) -> object:
        """Return the value of a known setting; KeyError when the key is unknown."""
        return self.values[key]

    def __setitem__(self, key: str, value: object) -> None:
        """Set a known setting; KeyError when unknown, ValueError when the value is invalid."""
        if key not in DEFAULTS:
            raise KeyError(key)
        self.values[key] = _validate(key, value)

    def get(self, key: str, default: object = None) -> object:
        """Return a setting value, or the default when the key is not present."""
        return self.values.get(key, default)

    def save(self) -> None:
        """Write the settings as JSON atomically, creating the parent folder."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        handle = None
        temp_name = ""
        try:
            descriptor, temp_name = tempfile.mkstemp(
                dir=self.path.parent, prefix=self.path.name + ".", suffix=".tmp"
            )
            handle = os.fdopen(descriptor, "w", encoding="utf-8")
            json.dump(self.values, handle, indent=2)
            handle.write("\n")
            handle.close()
            handle = None
            os.replace(temp_name, self.path)
            temp_name = ""
        finally:
            if handle is not None:
                handle.close()
            if temp_name:
                try:
                    os.unlink(temp_name)
                except OSError:
                    pass
