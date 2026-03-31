"""Deterministic twin reasoning engine with supportive and honest voices."""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any

from .runtime_client import InferenceClient, LocalHeuristicClient, ModelProfile, get_model_profile
from .schemas import GroundingMetadata, TwinContext, TwinResponse


class TwinReasoningEngine:
    """Generate dual voice responses from local context without model calls."""

    def __init__(
        self,
        inference_client: InferenceClient | None = None,
        model_profile: ModelProfile | None = None,
        strict_runtime: bool = True,
    ) -> None:
        self._fallback_client = LocalHeuristicClient()
        self._inference_client = inference_client or self._fallback_client
        self._model_profile = model_profile or get_model_profile("8gb")
        self._strict_runtime = strict_runtime

    def generate_dual_response(self, user_text: str, context: TwinContext) -> TwinResponse:
        if self._is_name_query(user_text):
            return self._generate_name_query_response(context)

        grounding = self._build_grounding(context)
        supportive, honest = self._generate_with_fallback(user_text, grounding)

        return TwinResponse(
            supportive_response=supportive,
            honest_response=honest,
            grounding=grounding if grounding.hints else None,
        )

    def _is_name_query(self, user_text: str) -> bool:
        normalized = " ".join((user_text or "").strip().lower().split())
        if not normalized:
            return False

        patterns = (
            "what is my name",
            "who am i",
            "my name",
        )
        return any(pattern in normalized for pattern in patterns)

    def _generate_name_query_response(self, context: TwinContext) -> TwinResponse:
        known_name = self._resolve_known_name(context)
        if known_name:
            return TwinResponse(
                supportive_response=(
                    f"Your name in local memory is {known_name}. "
                    "I can keep using it consistently in future planning responses."
                ),
                honest_response=(
                    f"Direct answer: your name appears to be {known_name} based on local memory."
                ),
                grounding=None,
            )

        return TwinResponse(
            supportive_response=(
                "Your name is not yet in local memory. "
                "Share it once and I can store it for future responses."
            ),
            honest_response=(
                "Direct answer: your name is not yet in local memory. "
                "Please provide it so it can be stored locally."
            ),
            grounding=None,
        )

    def _resolve_known_name(self, context: TwinContext) -> str | None:
        # Priority A: explicit profile name.
        profile_name = self._extract_profile_name(context.profile_snapshot)
        if profile_name:
            return profile_name

        # Priority B: infer from local path metadata values like /Users/<name>/...
        path_name = self._extract_name_from_event_paths(context.recent_events)
        if path_name:
            return path_name

        # Priority C: fallback metadata keys user/username/owner.
        metadata_name = self._extract_name_from_event_user_fields(context.recent_events)
        if metadata_name:
            return metadata_name

        return None

    def _extract_profile_name(self, profile_snapshot: dict[str, Any]) -> str | None:
        if not isinstance(profile_snapshot, dict):
            return None
        value = profile_snapshot.get("name")
        if isinstance(value, str) and value.strip():
            return value.strip()
        return None

    def _extract_name_from_event_paths(self, recent_events: list[dict[str, Any]]) -> str | None:
        for event in recent_events:
            if not isinstance(event, dict):
                continue
            metadata = event.get("metadata")
            for value in self._iter_nested_values([metadata]):
                if not isinstance(value, str):
                    continue
                match = re.search(r"/Users/([^/]+)/", value)
                if match:
                    candidate = match.group(1).strip()
                    if candidate:
                        return candidate
        return None

    def _extract_name_from_event_user_fields(self, recent_events: list[dict[str, Any]]) -> str | None:
        target_keys = {"user", "username", "owner"}
        for event in recent_events:
            if not isinstance(event, dict):
                continue
            metadata = event.get("metadata")
            for value in self._iter_nested_values([metadata]):
                if not isinstance(value, dict):
                    continue
                for key in target_keys:
                    raw = value.get(key)
                    if isinstance(raw, str) and raw.strip():
                        return raw.strip()
        return None

    def _iter_nested_values(self, values: Iterable[Any]) -> Iterable[Any]:
        for value in values:
            if isinstance(value, dict):
                yield value
                for nested in value.values():
                    yield from self._iter_nested_values([nested])
                continue
            if isinstance(value, list):
                for item in value:
                    yield from self._iter_nested_values([item])
                continue
            yield value

    def _generate_with_fallback(
        self,
        user_text: str,
        grounding: GroundingMetadata,
    ) -> tuple[str, str]:
        try:
            return self._inference_client.generate_dual_response(
                user_text,
                grounding,
                self._model_profile,
            )
        except Exception as exc:
            if self._strict_runtime:
                raise RuntimeError(
                    "Twin runtime inference failed and strict_runtime=True"
                ) from exc
            return self._fallback_client.generate_dual_response(
                user_text,
                grounding,
                self._model_profile,
            )

    def _build_grounding(self, context: TwinContext) -> GroundingMetadata:
        profile_tone = None
        if isinstance(context.profile_snapshot, dict):
            tone_value = context.profile_snapshot.get("tone")
            if isinstance(tone_value, str) and tone_value.strip():
                profile_tone = tone_value.strip()

        hints: list[str] = []
        if context.tags:
            hints.append(f"recent tags include {', '.join(context.tags[:2])}")
        if context.outcomes:
            hints.append(f"recent outcomes include {', '.join(context.outcomes[:2])}")
        if profile_tone:
            hints.append(f"profile tone is {profile_tone}")

        return GroundingMetadata(
            hints=hints,
            tags_used=context.tags[:2],
            outcomes_used=context.outcomes[:2],
            profile_tone=profile_tone,
        )
