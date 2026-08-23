"""Shared pytest fixtures."""

import pytest

import database


@pytest.fixture()
def temp_database(tmp_path, monkeypatch):
    """Point the database module at an empty file for one test.

    Shared across test files so nothing ever runs against the user's real
    protein_tracker.db.
    """
    database_path = tmp_path / "test_tracker.db"
    monkeypatch.setattr(database, "DATABASE_NAME", str(database_path))
    database.initialize_database()
    return database_path
