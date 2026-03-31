"""Ingestion services for persisting normalized records as events."""

from __future__ import annotations

from collections.abc import Callable

from u_core.memory import Event, SQLiteStore

from .models import NormalizedRecord


def ingest_records(
    store: SQLiteStore,
    records: list[NormalizedRecord],
    *,
    event_type: str = "ingest.record",
) -> list[Event]:
    """Persist normalized records as deterministic events."""
    events: list[Event] = []
    for record in records:
        metadata = {
            "source": record.source,
            "source_id": record.source_id,
            "tags": list(record.tags),
            **record.metadata,
        }
        events.append(store.create_event(event_type, record.content, metadata=metadata))
    return events


def ingest_text_with_parser(
    store: SQLiteStore,
    text: str,
    parser: Callable[[str], list[NormalizedRecord]],
    *,
    event_type: str = "ingest.record",
) -> list[Event]:
    """Parse text into normalized records and persist as events."""
    records = parser(text)
    return ingest_records(store, records, event_type=event_type)