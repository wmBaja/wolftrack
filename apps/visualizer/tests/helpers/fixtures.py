"""Shared pytest fixtures for backend tests."""
from __future__ import annotations

import os

import pytest

from tests.helpers.make_blf import SYNTHETIC_DBC, make_blf, synthetic_database


@pytest.fixture
def tmp_user_data(tmp_path, monkeypatch):
    """Point WOLFTRACK_USER_DATA at a temporary directory."""
    data_dir = tmp_path / "user_data"
    data_dir.mkdir()
    monkeypatch.setenv("WOLFTRACK_USER_DATA", str(data_dir))
    return data_dir


@pytest.fixture
def synthetic_dbc():
    """Parsed synthetic cantools database."""
    return synthetic_database()


@pytest.fixture
def synthetic_dbc_text() -> str:
    """Raw synthetic DBC text."""
    return SYNTHETIC_DBC


@pytest.fixture
def synthetic_blf(tmp_path):
    """Factory fixture: write a .blf from (ts, message_name, values) tuples."""

    def _make(frames, name: str = "session.blf") -> str:
        return make_blf(str(tmp_path / name), frames)

    return _make
