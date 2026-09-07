from __future__ import annotations

from pathlib import Path

import pytest

from macro_desk.config import Settings
from macro_desk.db.repository import DocumentRepository, connect, initialize


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(database_path=tmp_path / "macro_desk.sqlite")


@pytest.fixture
def repository(settings: Settings) -> DocumentRepository:
    connection = connect(settings.database_path)
    initialize(connection)
    try:
        yield DocumentRepository(connection)
    finally:
        connection.close()
