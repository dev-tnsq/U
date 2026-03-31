"""Graph-edge persistence APIs backed by SQLite."""

from __future__ import annotations

import json

from .models import GraphEdge
from .store import SQLiteStore, utc_now_iso


class GraphStore:
    def __init__(self, store: SQLiteStore) -> None:
        self.store = store

    def upsert_edge(
        self,
        source: str,
        target: str,
        relation: str,
        *,
        weight: float = 1.0,
        metadata: dict | None = None,
    ) -> GraphEdge:
        now = utc_now_iso()
        metadata = metadata or {}
        with self.store._conn:
            self.store._conn.execute(
                """
                INSERT INTO graph_edges(source, target, relation, weight, metadata_json, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(source, target, relation) DO UPDATE SET
                    weight = excluded.weight,
                    metadata_json = excluded.metadata_json,
                    updated_at = excluded.updated_at
                """,
                (source, target, relation, weight, json.dumps(metadata, separators=(",", ":")), now),
            )
        return GraphEdge(
            source=source,
            target=target,
            relation=relation,
            weight=weight,
            metadata=metadata,
            updated_at=now,
        )

    def list_edges(
        self,
        *,
        source: str | None = None,
        target: str | None = None,
        relation: str | None = None,
        limit: int = 100,
    ) -> list[GraphEdge]:
        query = "SELECT * FROM graph_edges"
        params = []
        filters = []
        if source is not None:
            filters.append("source = ?")
            params.append(source)
        if target is not None:
            filters.append("target = ?")
            params.append(target)
        if relation is not None:
            filters.append("relation = ?")
            params.append(relation)

        if filters:
            query += " WHERE " + " AND ".join(filters)
        query += " ORDER BY updated_at DESC LIMIT ?"
        params.append(limit)

        rows = self.store._conn.execute(query, tuple(params)).fetchall()
        return [
            GraphEdge(
                source=row["source"],
                target=row["target"],
                relation=row["relation"],
                weight=row["weight"],
                metadata=json.loads(row["metadata_json"] or "{}"),
                updated_at=row["updated_at"],
            )
            for row in rows
        ]
