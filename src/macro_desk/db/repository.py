from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional

from macro_desk.domain.classification import classify_document
from macro_desk.domain.importance import rank_importance
from macro_desk.domain.models import Document, IngestRun, NewDocument

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
    category TEXT NOT NULL,
    classification_reason TEXT NOT NULL,
    importance TEXT NOT NULL,
    importance_reason TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE (source_url),
    UNIQUE (content_hash)
);
"""

INGEST_RUN_SCHEMA = """
CREATE TABLE IF NOT EXISTS ingest_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT NOT NULL,
    finished_at TEXT NOT NULL,
    fetched INTEGER NOT NULL,
    inserted INTEGER NOT NULL,
    skipped INTEGER NOT NULL,
    failed INTEGER NOT NULL,
    errors TEXT NOT NULL
);
"""

INDEXES = """
CREATE INDEX IF NOT EXISTS idx_documents_published_at
    ON documents (published_at DESC);

CREATE INDEX IF NOT EXISTS idx_documents_document_type
    ON documents (document_type);

CREATE INDEX IF NOT EXISTS idx_documents_importance
    ON documents (importance);

CREATE INDEX IF NOT EXISTS idx_documents_created_at
    ON documents (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_ingest_runs_finished_at
    ON ingest_runs (finished_at DESC);
"""


def connect(database_path: Path) -> sqlite3.Connection:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(database_path))
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize(connection: sqlite3.Connection) -> None:
    connection.executescript(SCHEMA)
    connection.executescript(INGEST_RUN_SCHEMA)
    _ensure_classification_columns(connection)
    _ensure_importance_columns(connection)
    connection.executescript(INDEXES)
    _backfill_classifications(connection)
    _backfill_importance(connection)
    connection.commit()


def _table_columns(connection: sqlite3.Connection) -> set[str]:
    return {row["name"] for row in connection.execute("PRAGMA table_info(documents)")}


def _ensure_classification_columns(connection: sqlite3.Connection) -> None:
    columns = _table_columns(connection)
    if "category" not in columns:
        connection.execute("ALTER TABLE documents ADD COLUMN category TEXT")
    if "classification_reason" not in columns:
        connection.execute("ALTER TABLE documents ADD COLUMN classification_reason TEXT")


def _ensure_importance_columns(connection: sqlite3.Connection) -> None:
    columns = _table_columns(connection)
    if "importance" not in columns:
        connection.execute("ALTER TABLE documents ADD COLUMN importance TEXT")
    if "importance_reason" not in columns:
        connection.execute("ALTER TABLE documents ADD COLUMN importance_reason TEXT")


def _backfill_importance(connection: sqlite3.Connection) -> None:
    rows = connection.execute(
        """
        SELECT id, title, clean_text
        FROM documents
        WHERE importance IS NULL OR importance = ''
           OR importance_reason IS NULL OR importance_reason = ''
        """
    ).fetchall()
    for row in rows:
        result = rank_importance(row["title"], row["clean_text"])
        connection.execute(
            """
            UPDATE documents
            SET importance = ?, importance_reason = ?
            WHERE id = ?
            """,
            (result.importance, result.reason, row["id"]),
        )


def _backfill_classifications(connection: sqlite3.Connection) -> None:
    rows = connection.execute(
        """
        SELECT id, title, clean_text
        FROM documents
        WHERE category IS NULL OR category = ''
           OR classification_reason IS NULL OR classification_reason = ''
        """
    ).fetchall()
    for row in rows:
        result = classify_document(row["title"], row["clean_text"])
        connection.execute(
            """
            UPDATE documents
            SET category = ?, classification_reason = ?
            WHERE id = ?
            """,
            (result.category, result.reason, row["id"]),
        )


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
        category=row["category"],
        classification_reason=row["classification_reason"],
        importance=row["importance"],
        importance_reason=row["importance_reason"],
        created_at=_parse_datetime(row["created_at"]),
    )


def _row_to_ingest_run(row: sqlite3.Row) -> IngestRun:
    raw_errors = row["errors"]
    try:
        errors = json.loads(raw_errors) if raw_errors else []
    except json.JSONDecodeError:
        errors = [raw_errors]
    if not isinstance(errors, list):
        errors = [str(errors)]
    return IngestRun(
        id=row["id"],
        started_at=_parse_datetime(row["started_at"]),
        finished_at=_parse_datetime(row["finished_at"]),
        fetched=row["fetched"],
        inserted=row["inserted"],
        skipped=row["skipped"],
        failed=row["failed"],
        errors=[str(item) for item in errors],
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
                    raw_text, clean_text, content_hash, category,
                    classification_reason, importance, importance_reason, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    document.category,
                    document.classification_reason,
                    document.importance,
                    document.importance_reason,
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

    def list_newest(
        self,
        limit: int = 50,
        category: Optional[str] = None,
        document_type: Optional[str] = None,
        importance: Optional[str] = None,
    ) -> list[Document]:
        clauses = []
        params: list[object] = []
        if category:
            clauses.append("category = ?")
            params.append(category)
        if document_type:
            clauses.append("document_type = ?")
            params.append(document_type)
        if importance:
            clauses.append("importance = ?")
            params.append(importance)
        where = "WHERE {}".format(" AND ".join(clauses)) if clauses else ""
        params.append(limit)
        rows: Iterable[sqlite3.Row] = self._connection.execute(
            """
            SELECT * FROM documents
            {}
            ORDER BY published_at DESC, created_at DESC, id DESC
            LIMIT ?
            """.format(where),
            params,
        ).fetchall()
        return [_row_to_document(row) for row in rows]

    def list_first_seen_since(
        self,
        since: datetime,
        limit: int = 200,
        rank_by_importance: bool = False,
    ) -> list[Document]:
        """Documents whose first insert time falls on or after ``since``."""
        order = "created_at DESC, id DESC"
        if rank_by_importance:
            order = (
                "CASE importance WHEN 'high' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END, "
                "created_at DESC, id DESC"
            )
        rows: Iterable[sqlite3.Row] = self._connection.execute(
            """
            SELECT * FROM documents
            WHERE created_at >= ?
            ORDER BY {}
            LIMIT ?
            """.format(order),
            (since.isoformat(), limit),
        ).fetchall()
        return [_row_to_document(row) for row in rows]

    def record_ingest_run(
        self,
        started_at: datetime,
        finished_at: datetime,
        fetched: int,
        inserted: int,
        skipped: int,
        failed: int,
        errors: Optional[list[str]] = None,
    ) -> IngestRun:
        cursor = self._connection.execute(
            """
            INSERT INTO ingest_runs (
                started_at, finished_at, fetched, inserted, skipped, failed, errors
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                started_at.isoformat(),
                finished_at.isoformat(),
                fetched,
                inserted,
                skipped,
                failed,
                json.dumps(errors or []),
            ),
        )
        self._connection.commit()
        stored = self.get_ingest_run(cursor.lastrowid)
        if stored is None:  # pragma: no cover
            raise RuntimeError("Failed to persist ingest run")
        return stored

    def get_ingest_run(self, run_id: int) -> Optional[IngestRun]:
        row = self._connection.execute(
            "SELECT * FROM ingest_runs WHERE id = ?",
            (run_id,),
        ).fetchone()
        return _row_to_ingest_run(row) if row else None

    def list_ingest_runs_since(self, since: datetime, limit: int = 50) -> list[IngestRun]:
        rows: Iterable[sqlite3.Row] = self._connection.execute(
            """
            SELECT * FROM ingest_runs
            WHERE finished_at >= ?
            ORDER BY finished_at DESC, id DESC
            LIMIT ?
            """,
            (since.isoformat(), limit),
        ).fetchall()
        return [_row_to_ingest_run(row) for row in rows]
