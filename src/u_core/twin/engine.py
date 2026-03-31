"""Deterministic twin reasoning engine with supportive and honest voices."""

from __future__ import annotations

from .schemas import GroundingMetadata, TwinContext, TwinResponse


class TwinReasoningEngine:
    """Generate dual voice responses from local context without model calls."""

    def generate_dual_response(self, user_text: str, context: TwinContext) -> TwinResponse:
        cleaned_text = (user_text or "").strip() or "that"
        grounding = self._build_grounding(context)

        supportive = self._build_supportive_response(cleaned_text, grounding)
        honest = self._build_honest_response(cleaned_text, grounding)

        return TwinResponse(
            supportive_response=supportive,
            honest_response=honest,
            grounding=grounding if grounding.hints else None,
        )

    def _build_supportive_response(self, user_text: str, grounding: GroundingMetadata) -> str:
        base = f"You are moving in the right direction with {user_text}."
        if grounding.profile_tone:
            base += f" I will match your preferred {grounding.profile_tone} tone while helping you plan the next step."
        else:
            base += " I will keep this practical and calm so you can make progress." 

        if grounding.hints:
            base += f" Grounding hint: {grounding.hints[0]}."
        return base

    def _build_honest_response(self, user_text: str, grounding: GroundingMetadata) -> str:
        base = f"Direct take: {user_text} needs a concrete tradeoff decision and a short execution plan."
        if grounding.outcomes_used:
            base += f" Prior outcomes suggest you should preserve what worked: {grounding.outcomes_used[0]}."
        elif grounding.tags_used:
            base += f" Your recent focus tag is {grounding.tags_used[0]}, so avoid unrelated tasks."
        else:
            base += " There is limited prior memory, so start small and measure one clear result."
        return base

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
