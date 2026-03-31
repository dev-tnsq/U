"""Deterministic twin reasoning engine with supportive and honest voices."""

from __future__ import annotations

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
        grounding = self._build_grounding(context)
        supportive, honest = self._generate_with_fallback(user_text, grounding)

        return TwinResponse(
            supportive_response=supportive,
            honest_response=honest,
            grounding=grounding if grounding.hints else None,
        )

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
