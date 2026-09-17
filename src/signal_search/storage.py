"""Persistent document storage implementations."""

import sqlite3
from pathlib import Path
from threading import RLock
from typing import Protocol


class DocumentStore(Protocol):
    """Storage contract used by the search engine."""

    def load_documents(self) -> dict[str, str]: ...

    def upsert_document(self, document_id: str, text: str) -> None: ...

    def upsert_documents(self, documents: dict[str, str]) -> None: ...

    def delete_document(self, document_id: str) -> bool: ...

    def clear(self) -> None: ...

    def close(self) -> None: ...


class SQLiteDocumentStore:
    """Store searchable documents in a local SQLite database."""

    def __init__(self, database_path: str | Path) -> None:
        raw_path = str(database_path)
        if raw_path == ":memory:":
            path = raw_path
        else:
            resolved_path = Path(raw_path).expanduser().resolve()
            resolved_path.parent.mkdir(parents=True, exist_ok=True)
            path = str(resolved_path)

        self.database_path = path
        self._lock = RLock()
        self._connection = sqlite3.connect(path, check_same_thread=False)
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS documents (
                document_id TEXT PRIMARY KEY,
                text TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        self._connection.commit()

    def load_documents(self) -> dict[str, str]:
        """Load all stored documents in deterministic ID order."""
        with self._lock:
            rows = self._connection.execute(
                "SELECT document_id, text FROM documents ORDER BY document_id"
            ).fetchall()

        return {document_id: text for document_id, text in rows}

    def upsert_document(self, document_id: str, text: str) -> None:
        """Insert a document or replace its text."""
        with self._lock, self._connection:
            self._connection.execute(
                """
                INSERT INTO documents (document_id, text, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(document_id) DO UPDATE SET
                    text = excluded.text,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (document_id, text),
            )

    def upsert_documents(self, documents: dict[str, str]) -> None:
        """Insert or replace multiple documents in one transaction."""
        rows = [(document_id, text) for document_id, text in documents.items()]
        with self._lock, self._connection:
            self._connection.executemany(
                """
                INSERT INTO documents (document_id, text, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(document_id) DO UPDATE SET
                    text = excluded.text,
                    updated_at = CURRENT_TIMESTAMP
                """,
                rows,
            )

    def delete_document(self, document_id: str) -> bool:
        """Delete a document and report whether it existed."""
        with self._lock, self._connection:
            cursor = self._connection.execute(
                "DELETE FROM documents WHERE document_id = ?",
                (document_id,),
            )
        return cursor.rowcount > 0

    def clear(self) -> None:
        """Delete all stored documents."""
        with self._lock, self._connection:
            self._connection.execute("DELETE FROM documents")

    def close(self) -> None:
        """Close the SQLite connection."""
        with self._lock:
            self._connection.close()

    def __enter__(self) -> "SQLiteDocumentStore":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
