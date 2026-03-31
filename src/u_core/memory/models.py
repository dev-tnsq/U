"""Typed models for memory-core entities."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Event:
    event_type: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    id: int | None = None
    created_at: str | None = None


@dataclass
class Reflection:
    kind: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    id: int | None = None
    created_at: str | None = None


@dataclass
class Profile:
    profile_id: str
    data: dict[str, Any]
    version: int
    updated_at: str


@dataclass
class GraphEdge:
    source: str
    target: str
    relation: str
    weight: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)
    updated_at: str | None = None
