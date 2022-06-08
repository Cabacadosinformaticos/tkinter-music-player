# Tests for the history factory: BACKENDS, the backend built for each kind and
# the error for an unknown kind. The SQL Server backend is only constructed, it
# never connects here.

from __future__ import annotations

import sys

import pytest

import music_player.history as history_package
from music_player.history import (
    BACKENDS,
    HistoryBackend,
    SqlServerHistory,
    SqliteHistory,
    TextHistory,
    make_backend,
)


def test_backends_mapping_has_every_kind():
    assert set(BACKENDS) == {"sqlite", "text", "sqlserver"}


def test_make_backend_sqlite(tmp_path):
    backend = make_backend("sqlite", data_path=tmp_path)
    assert isinstance(backend, SqliteHistory)
    assert isinstance(backend, HistoryBackend)
    assert backend.name == "sqlite"
    assert backend.path == tmp_path / "history.db"


def test_make_backend_text(tmp_path):
    backend = make_backend("text", data_path=tmp_path)
    assert isinstance(backend, TextHistory)
    assert backend.name == "text"
    assert backend.path == tmp_path / "history.txt"


def test_make_backend_sqlserver_only_constructs(tmp_path):
    config_path = tmp_path / "db_config.ini"
    backend = make_backend("sqlserver", db_config_path=config_path)
    assert isinstance(backend, SqlServerHistory)
    assert backend.name == "sqlserver"
    assert backend.config_path == config_path


def test_make_backend_unknown_kind_raises_value_error(tmp_path):
    with pytest.raises(ValueError):
        make_backend("nope", data_path=tmp_path)


def test_importing_the_package_does_not_import_pyodbc(monkeypatch):
    monkeypatch.delitem(sys.modules, "pyodbc", raising=False)
    # Touching the SQL Server class must not import pyodbc either.
    assert history_package.SqlServerHistory is SqlServerHistory
    assert "pyodbc" not in sys.modules
