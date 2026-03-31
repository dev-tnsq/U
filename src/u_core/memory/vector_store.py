"""Vector storage abstraction with local in-memory fallback."""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from typing import Any


class VectorStore(ABC):
    @abstractmethod
    def upsert(self, key: str, vector: list[float], metadata: dict[str, Any] | None = None) -> None:
        raise NotImplementedError

    @abstractmethod
    def query(self, vector: list[float], top_k: int = 5) -> list[tuple[str, float, dict[str, Any]]]:
        raise NotImplementedError


class InMemoryVectorStore(VectorStore):
    """Small-footprint fallback suitable for offline local development."""

    def __init__(self) -> None:
        self._vectors: dict[str, tuple[list[float], dict[str, Any]]] = {}

    def upsert(self, key: str, vector: list[float], metadata: dict[str, Any] | None = None) -> None:
        self._vectors[key] = (vector, metadata or {})

    def query(self, vector: list[float], top_k: int = 5) -> list[tuple[str, float, dict[str, Any]]]:
        scored: list[tuple[str, float, dict[str, Any]]] = []
        for key, (stored_vector, metadata) in self._vectors.items():
            score = _cosine_similarity(vector, stored_vector)
            scored.append((key, score, metadata))
        scored.sort(key=lambda item: item[1], reverse=True)
        return scored[:top_k]


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    if len(a) != len(b) or not a:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)
