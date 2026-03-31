"""Twin context assembly from local memory stores."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from u_core.memory import GraphStore, ProfileStore, SQLiteStore

from .schemas import TwinContext


def build_twin_context(
    store: SQLiteStore,
    *,
    profile_store: ProfileStore | None = None,
    graph_store: GraphStore | None = None,
    event_limit: int = 8,
    reflection_limit: int = 6,
    edge_limit: int = 10,
) -> TwinContext:
    """Build a memory-grounded context object for twin reasoning."""

    profile_store = profile_store or ProfileStore(store)
    graph_store = graph_store or GraphStore(store)

    events = store.list_events(limit=event_limit)
    reflections = store.list_reflections(limit=reflection_limit)
    profile = profile_store.load_profile()
    edges = graph_store.list_edges(limit=edge_limit)

    recent_events: list[dict[str, Any]] = [
        {
            "id": event.id,
            "event_type": event.event_type,
            "content": event.content,
            "metadata": event.metadata,
            "created_at": event.created_at,
        }
        for event in events
    ]
    recent_reflections: list[dict[str, Any]] = [
        {
            "id": reflection.id,
            "kind": reflection.kind,
            "content": reflection.content,
            "metadata": reflection.metadata,
            "created_at": reflection.created_at,
        }
        for reflection in reflections
    ]
    profile_snapshot = profile.data if profile is not None else {}
    graph_edges: list[dict[str, Any]] = [
        {
            "source": edge.source,
            "target": edge.target,
            "relation": edge.relation,
            "weight": edge.weight,
            "metadata": edge.metadata,
            "updated_at": edge.updated_at,
        }
        for edge in edges
    ]

    tags = _collect_unique_tags(recent_events, recent_reflections, graph_edges, profile_snapshot)
    outcomes = _collect_unique_outcomes(recent_events, recent_reflections, profile_snapshot)

    return TwinContext(
        recent_events=recent_events,
        recent_reflections=recent_reflections,
        profile_snapshot=profile_snapshot,
        graph_edges=graph_edges,
        tags=tags,
        outcomes=outcomes,
    )


def _collect_unique_tags(*sources: Any) -> list[str]:
    tags: list[str] = []
    for value in _iter_nested_values(sources):
        if isinstance(value, str):
            continue
        if isinstance(value, dict) and "tags" in value:
            for tag in _normalize_string_list(value.get("tags")):
                if tag not in tags:
                    tags.append(tag)
    return tags


def _collect_unique_outcomes(*sources: Any) -> list[str]:
    outcomes: list[str] = []
    for value in _iter_nested_values(sources):
        if isinstance(value, dict):
            for key in ("outcome", "outcomes", "result", "results"):
                if key not in value:
                    continue
                for item in _normalize_string_list(value.get(key)):
                    if item not in outcomes:
                        outcomes.append(item)
    return outcomes


def _normalize_string_list(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if isinstance(value, Iterable):
        values: list[str] = []
        for item in value:
            if isinstance(item, str) and item.strip():
                values.append(item.strip())
        return values
    return []


def _iter_nested_values(values: Iterable[Any]) -> Iterable[Any]:
    for value in values:
        if isinstance(value, dict):
            yield value
            for nested in value.values():
                yield from _iter_nested_values([nested])
            continue
        if isinstance(value, list):
            for item in value:
                yield from _iter_nested_values([item])
            continue
        yield value
