"""Shared data model for deterministic local ingestion parsers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class NormalizedRecord:
    """Canonical ingestion record suitable for event persistence."""

    source: str
    source_id: str
    content: str
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
