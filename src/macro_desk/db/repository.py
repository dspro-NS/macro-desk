from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional

from macro_desk.domain.models import Document, NewDocument

SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    published_at TEXT NOT NULL,
    source TEXT NOT NULL,
    source_url TEXT NOT NULL,
    document_type TEXT NOT NULL,
    raw_text TEXT NOT NULL,
    clean_text TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE (source_url),
    UNIQUE (content_hash)
);

CREATE INDEX IF NOT EXISTS idx_documents_published_at
    ON documents (published_at DESC);
"""


def connect(database_path: Path) -> sqlite3.Connection:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(database_path))
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize(connection: sqlite3.Connection) -> None:
    connection.executescript(SCHEMA)
    connection.commit()


def _parse_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def _row_to_document(row: sqlite3.Row) -> Document:
    return Document(
        id=row["id"],
        title=row["title"],
        published_at=_parse_datetime(row["published_at"]),
        source=row["source"],
        source_url=row["source_url"],
        document_type=row["document_type"],
        raw_text=row["raw_text"],
        clean_text=row["clean_text"],
        content_hash=row["content_hash"],
        created_at=_parse_datetime(row["created_at"]),
    )


class DocumentRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def insert(self, document: NewDocument, created_at: Optional[datetime] = None) -> Optional[Document]:
        """Insert a document. Returns None when URL or content hash already exists."""
        created = created_at or datetime.now(timezone.utc)
        try:
            cursor = self._connection.execute(
                """
                INSERT INTO documents (
                    title, published_at, source, source_url, document_type,
                    raw_text, clean_text, content_hash, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    document.title,
                    document.published_at.isoformat(),
                    document.source,
                    document.source_url,
                    document.document_type,
                    document.raw_text,
                    document.clean_text,
                    document.content_hash,
                    created.isoformat(),
                ),
            )
            self._connection.commit()
        except sqlite3.IntegrityError:
            return None
        return self.get_by_id(cursor.lastrowid)

    def get_by_id(self, document_id: int) -> Optional[Document]:
        row = self._connection.execute(
            "SELECT * FROM documents WHERE id = ?",
            (document_id,),
        ).fetchone()
        return _row_to_document(row) if row else None

    def exists_by_source_url(self, source_url: str) -> bool:
        row = self._connection.execute(
            "SELECT 1 FROM documents WHERE source_url = ? LIMIT 1",
            (source_url,),
        ).fetchone()
        return row is not None

    def exists_by_content_hash(self, content_hash: str) -> bool:
        row = self._connection.execute(
            "SELECT 1 FROM documents WHERE content_hash = ? LIMIT 1",
            (content_hash,),
        ).fetchone()
        return row is not None

    def list_newest(self, limit: int = 50) -> list[Document]:
        rows: Iterable[sqlite3.Row] = self._connection.execute(
            """
            SELECT * FROM documents
            ORDER BY published_at DESC, created_at DESC, id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [_row_to_document(row) for row in rows]
