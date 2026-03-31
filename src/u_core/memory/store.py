"""SQLite-backed storage primitives for memory-core."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import Event, Reflection


def utc_now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


class SQLiteStore:
    """Thin SQLite wrapper with schema bootstrap and memory CRUD APIs."""

    SCHEMA_VERSION = 1

    def __init__(self, db_path: str | Path, schema_path: str | Path | None = None) -> None:
        self.db_path = Path(db_path)
        self.schema_path = (
            Path(schema_path)
            if schema_path is not None
            else Path(__file__).with_name("schema.sql")
        )
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL;")
        self._conn.execute("PRAGMA foreign_keys=ON;")

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "SQLiteStore":
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.close()

    def initialize(self) -> None:
        """Initialize database and apply baseline schema migration."""
        schema_sql = self.schema_path.read_text(encoding="utf-8")
        with self._conn:
            self._conn.executescript(schema_sql)
            cursor = self._conn.execute(
                "SELECT 1 FROM schema_migrations WHERE version = ?",
                (self.SCHEMA_VERSION,),
            )
            if cursor.fetchone() is None:
                self._conn.execute(
                    "INSERT INTO schema_migrations(version, applied_at) VALUES (?, ?)",
                    (self.SCHEMA_VERSION, utc_now_iso()),
                )

    def create_event(self, event_type: str, content: str, metadata: dict[str, Any] | None = None) -> Event:
        created_at = utc_now_iso()
        metadata_json = json.dumps(metadata or {}, separators=(",", ":"))
        with self._conn:
            cursor = self._conn.execute(
                """
                INSERT INTO events(event_type, content, metadata_json, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (event_type, content, metadata_json, created_at),
            )
        return Event(
            id=int(cursor.lastrowid or 0),
            event_type=event_type,
            content=content,
            metadata=metadata or {},
            created_at=created_at,
        )

    def get_event(self, event_id: int) -> Event | None:
        row = self._conn.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
        if row is None:
            return None
        return Event(
            id=row["id"],
            event_type=row["event_type"],
            content=row["content"],
            metadata=json.loads(row["metadata_json"] or "{}"),
            created_at=row["created_at"],
        )

    def list_events(self, limit: int = 100, event_type: str | None = None) -> list[Event]:
        if event_type is None:
            rows = self._conn.execute(
                "SELECT * FROM events ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM events WHERE event_type = ? ORDER BY id DESC LIMIT ?",
                (event_type, limit),
            ).fetchall()
        return [
            Event(
                id=row["id"],
                event_type=row["event_type"],
                content=row["content"],
                metadata=json.loads(row["metadata_json"] or "{}"),
                created_at=row["created_at"],
            )
            for row in rows
        ]

    def update_event(
        self,
        event_id: int,
        *,
        content: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Event | None:
        current = self.get_event(event_id)
        if current is None:
            return None

        next_content = content if content is not None else current.content
        next_metadata = metadata if metadata is not None else current.metadata
        with self._conn:
            self._conn.execute(
                "UPDATE events SET content = ?, metadata_json = ? WHERE id = ?",
                (next_content, json.dumps(next_metadata, separators=(",", ":")), event_id),
            )
        return self.get_event(event_id)

    def delete_event(self, event_id: int) -> bool:
        with self._conn:
            cursor = self._conn.execute("DELETE FROM events WHERE id = ?", (event_id,))
        return cursor.rowcount > 0

    def create_reflection(self, kind: str, content: str, metadata: dict[str, Any] | None = None) -> Reflection:
        created_at = utc_now_iso()
        metadata_json = json.dumps(metadata or {}, separators=(",", ":"))
        with self._conn:
            cursor = self._conn.execute(
                """
                INSERT INTO reflections(kind, content, metadata_json, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (kind, content, metadata_json, created_at),
            )
        return Reflection(
            id=int(cursor.lastrowid or 0),
            kind=kind,
            content=content,
            metadata=metadata or {},
            created_at=created_at,
        )

    def get_reflection(self, reflection_id: int) -> Reflection | None:
        row = self._conn.execute("SELECT * FROM reflections WHERE id = ?", (reflection_id,)).fetchone()
        if row is None:
            return None
        return Reflection(
            id=row["id"],
            kind=row["kind"],
            content=row["content"],
            metadata=json.loads(row["metadata_json"] or "{}"),
            created_at=row["created_at"],
        )

    def list_reflections(self, limit: int = 100, kind: str | None = None) -> list[Reflection]:
        if kind is None:
            rows = self._conn.execute(
                "SELECT * FROM reflections ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM reflections WHERE kind = ? ORDER BY id DESC LIMIT ?",
                (kind, limit),
            ).fetchall()
        return [
            Reflection(
                id=row["id"],
                kind=row["kind"],
                content=row["content"],
                metadata=json.loads(row["metadata_json"] or "{}"),
                created_at=row["created_at"],
            )
            for row in rows
        ]

    def update_reflection(
        self,
        reflection_id: int,
        *,
        content: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Reflection | None:
        current = self.get_reflection(reflection_id)
        if current is None:
            return None

        next_content = content if content is not None else current.content
        next_metadata = metadata if metadata is not None else current.metadata
        with self._conn:
            self._conn.execute(
                "UPDATE reflections SET content = ?, metadata_json = ? WHERE id = ?",
                (next_content, json.dumps(next_metadata, separators=(",", ":")), reflection_id),
            )
        return self.get_reflection(reflection_id)

    def delete_reflection(self, reflection_id: int) -> bool:
        with self._conn:
            cursor = self._conn.execute("DELETE FROM reflections WHERE id = ?", (reflection_id,))
        return cursor.rowcount > 0
