"""Typed structures for twin reasoning inputs and outputs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TwinContext:
    """Context assembled from memory stores for local twin reasoning."""

    recent_events: list[dict[str, Any]] = field(default_factory=list)
    recent_reflections: list[dict[str, Any]] = field(default_factory=list)
    profile_snapshot: dict[str, Any] = field(default_factory=dict)
    graph_edges: list[dict[str, Any]] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    outcomes: list[str] = field(default_factory=list)


@dataclass
class GroundingMetadata:
    """Optional metadata showing how responses were grounded in memory."""

    hints: list[str] = field(default_factory=list)
    tags_used: list[str] = field(default_factory=list)
    outcomes_used: list[str] = field(default_factory=list)
    profile_tone: str | None = None


@dataclass
class TwinResponse:
    """Dual-voice response output from the twin reasoning engine."""

    supportive_response: str
    honest_response: str
    grounding: GroundingMetadata | None = None
