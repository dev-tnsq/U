"""Deterministic local benchmarking helpers for model recommendation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence
import re

_PROMPT_SUITE: tuple[str, ...] = (
    "You have 10 minutes to recover a derailed workday. Give a concrete 3-step plan.",
    "A teammate disagrees with your proposal. Offer a respectful response plus one compromise.",
    "Turn this vague goal into one measurable next action: improve product reliability.",
)

_ACTION_KEYWORDS = (
    "plan",
    "step",
    "next",
    "measure",
    "focus",
    "tradeoff",
    "decide",
    "action",
)

_NOISY_PATTERNS = (
    "as an ai",
    "i cannot",
    "i can't",
    "i do not have",
)


@dataclass(frozen=True)
class PromptBenchmark:
    """Single prompt evaluation for a model run."""

    prompt: str
    response: str
    latency_ms: float
    quality_score: float
    latency_score: float
    combined_score: float


@dataclass(frozen=True)
class ModelBenchmarkSummary:
    """Aggregate benchmark summary for one model."""

    model_name: str
    recommended_profile: str
    prompt_results: tuple[PromptBenchmark, ...]
    average_latency_ms: float
    average_quality_score: float
    average_latency_score: float
    overall_score: float


def prompt_suite() -> tuple[str, ...]:
    """Return the fixed benchmark prompt suite."""

    return _PROMPT_SUITE


def parse_model_size_billions(model_name: str) -> float | None:
    """Extract model size in billions from model name when present."""

    normalized = (model_name or "").strip().lower()
    if not normalized:
        return None

    match = re.search(r"(\d+(?:\.\d+)?)\s*b\b", normalized)
    if not match:
        return None

    return float(match.group(1))


def recommend_profile_for_model(model_name: str) -> str:
    """Map model names to the most stable local profile choice."""

    size_b = parse_model_size_billions(model_name)
    if size_b is None:
        return "8gb"

    if size_b <= 4.0:
        return "8gb"
    return "16gb"


def score_quality(response: str) -> float:
    """Score response quality using deterministic textual heuristics."""

    text = (response or "").strip()
    if not text:
        return 0.0

    lowered = text.lower()
    words = re.findall(r"\b\w+\b", lowered)
    word_count = len(words)

    sentence_count = len([part for part in re.split(r"[.!?]+", text) if part.strip()])

    score = 0.0

    if 18 <= word_count <= 140:
        score += 0.35
    elif 8 <= word_count <= 200:
        score += 0.2
    else:
        score += 0.05

    if 2 <= sentence_count <= 5:
        score += 0.25
    elif sentence_count == 1:
        score += 0.1

    if any(keyword in lowered for keyword in _ACTION_KEYWORDS):
        score += 0.25

    if any(pattern in lowered for pattern in _NOISY_PATTERNS):
        score -= 0.2

    if "?" in text:
        score -= 0.05

    return max(0.0, min(1.0, score))


def score_latency(latency_ms: float) -> float:
    """Convert latency to a normalized quality-preserving score."""

    if latency_ms <= 1500:
        return 1.0
    if latency_ms <= 3000:
        return 0.8
    if latency_ms <= 5000:
        return 0.6
    if latency_ms <= 8000:
        return 0.4
    return 0.2


def build_prompt_benchmark(prompt: str, response: str, latency_ms: float) -> PromptBenchmark:
    """Create a prompt-level benchmark with all derived deterministic scores."""

    quality = score_quality(response)
    latency = score_latency(latency_ms)
    combined = (quality * 0.7) + (latency * 0.3)

    return PromptBenchmark(
        prompt=prompt,
        response=response,
        latency_ms=latency_ms,
        quality_score=quality,
        latency_score=latency,
        combined_score=combined,
    )


def aggregate_model_score(model_name: str, prompt_results: Sequence[PromptBenchmark]) -> ModelBenchmarkSummary:
    """Aggregate per-prompt benchmark results for a single model."""

    if not prompt_results:
        raise ValueError("prompt_results must not be empty")

    results = tuple(prompt_results)
    average_latency_ms = sum(item.latency_ms for item in results) / len(results)
    average_quality_score = sum(item.quality_score for item in results) / len(results)
    average_latency_score = sum(item.latency_score for item in results) / len(results)
    overall_score = sum(item.combined_score for item in results) / len(results)

    return ModelBenchmarkSummary(
        model_name=model_name,
        recommended_profile=recommend_profile_for_model(model_name),
        prompt_results=results,
        average_latency_ms=average_latency_ms,
        average_quality_score=average_quality_score,
        average_latency_score=average_latency_score,
        overall_score=overall_score,
    )


def select_best_model(summaries: Sequence[ModelBenchmarkSummary]) -> ModelBenchmarkSummary | None:
    """Select best benchmarked model by score, then latency, then name."""

    if not summaries:
        return None

    return max(
        summaries,
        key=lambda item: (
            item.overall_score,
            item.average_quality_score,
            -item.average_latency_ms,
            item.model_name,
        ),
    )
