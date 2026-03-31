"""Reflection writing utilities for planner execution outcomes."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from u_core.memory import GraphStore, ProfileStore, Reflection, SQLiteStore


@dataclass
class PlannerExecutionOutcome:
    """Deterministic planner execution result consumed by reflection engine."""

    goal: str
    executed: bool
    actions: list[str] = field(default_factory=list)
    results: list[str] = field(default_factory=list)
    success: bool | None = None
    reviewer: str | None = None
    tags: list[str] = field(default_factory=list)
    profile_updates: dict[str, Any] = field(default_factory=dict)


@dataclass
class ReflectionApplyResult:
    """Result payload after writing reflection and memory updates."""

    reflection: Reflection
    profile_version: int
    edge_count: int


def apply_execution_reflection(
    store: SQLiteStore,
    outcome: PlannerExecutionOutcome,
    *,
    profile_store: ProfileStore | None = None,
    graph_store: GraphStore | None = None,
    profile_id: str = "default",
) -> ReflectionApplyResult:
    """Persist a reflection and derived profile/graph updates."""
    profile_store = profile_store or ProfileStore(store)
    graph_store = graph_store or GraphStore(store)

    reflection = store.create_reflection(
        kind="planner_execution",
        content=_build_reflection_content(outcome),
        metadata={
            "goal": outcome.goal,
            "executed": outcome.executed,
            "success": outcome.success,
            "actions": outcome.actions,
            "results": outcome.results,
            "reviewer": outcome.reviewer,
            "tags": outcome.tags,
        },
    )

    profile = _update_profile(profile_store, outcome, profile_id=profile_id)
    edges = _upsert_edges(graph_store, outcome)

    return ReflectionApplyResult(
        reflection=reflection,
        profile_version=profile.version,
        edge_count=edges,
    )


def _build_reflection_content(outcome: PlannerExecutionOutcome) -> str:
    action_count = len(outcome.actions)
    result_count = len(outcome.results)
    status = _status_label(outcome)
    return (
        f"Planner goal '{outcome.goal}' ended with status {status}; "
        f"actions={action_count}, results={result_count}."
    )


def _status_label(outcome: PlannerExecutionOutcome) -> str:
    if not outcome.executed:
        return "not-executed"
    if outcome.success is False:
        return "failed"
    if outcome.success is True:
        return "succeeded"
    return "executed"


def _normalize_goal(goal: str) -> str:
    cleaned = " ".join((goal or "").strip().lower().split())
    if not cleaned:
        return "unknown-goal"
    return cleaned.replace(" ", "-")


def _merge_recent_values(current: list[Any], value: Any, *, limit: int = 10) -> list[Any]:
    next_values = [item for item in current if item != value]
    next_values.insert(0, value)
    return next_values[:limit]


def _update_profile(
    profile_store: ProfileStore,
    outcome: PlannerExecutionOutcome,
    *,
    profile_id: str,
):
    existing = profile_store.load_profile(profile_id)
    profile_data: dict[str, Any] = {} if existing is None else dict(existing.data)

    existing_goals = profile_data.get("recent_goals")
    if not isinstance(existing_goals, list):
        existing_goals = []

    profile_data["recent_goals"] = _merge_recent_values(existing_goals, outcome.goal)
    profile_data["last_execution_status"] = _status_label(outcome)
    if outcome.tags:
        profile_data["focus_tags"] = list(dict.fromkeys([tag.strip().lower() for tag in outcome.tags if tag.strip()]))

    profile_data.update(outcome.profile_updates)
    return profile_store.update_profile(profile_data, profile_id=profile_id)


def _upsert_edges(graph_store: GraphStore, outcome: PlannerExecutionOutcome) -> int:
    goal_node = f"goal:{_normalize_goal(outcome.goal)}"
    relation = "planned"
    weight = 0.25
    if outcome.executed:
        relation = "attempted"
        weight = 0.7
    if outcome.executed and outcome.success is True:
        relation = "completed"
        weight = 1.0
    if outcome.executed and outcome.success is False:
        relation = "failed"
        weight = 0.4

    graph_store.upsert_edge(
        "planner",
        goal_node,
        relation,
        weight=weight,
        metadata={
            "actions": len(outcome.actions),
            "results": len(outcome.results),
            "reviewer": outcome.reviewer,
        },
    )

    edge_count = 1
    for tag in outcome.tags:
        cleaned = tag.strip().lower()
        if not cleaned:
            continue
        graph_store.upsert_edge(
            goal_node,
            f"tag:{cleaned}",
            "has_tag",
            weight=1.0,
            metadata={"goal": outcome.goal},
        )
        edge_count += 1

    return edge_count
