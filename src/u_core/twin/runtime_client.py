"""Local inference runtime abstractions for twin reasoning."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from subprocess import CalledProcessError, CompletedProcess, run
from typing import Callable, Protocol

from .schemas import GroundingMetadata


@dataclass(frozen=True)
class ModelProfile:
    """Configuration profile for local model execution."""

    name: str
    model_name: str
    context_window: int
    max_tokens: int
    temperature: float = 0.0
    extra_options: dict[str, int | float | str] = field(default_factory=dict)


_PROFILE_8GB = ModelProfile(
    name="8gb",
    model_name="llama3.2:3b",
    context_window=2048,
    max_tokens=256,
    temperature=0.0,
)

_PROFILE_16GB = ModelProfile(
    name="16gb",
    model_name="llama3.1:8b",
    context_window=4096,
    max_tokens=384,
    temperature=0.0,
)


def get_model_profile(name: str | None) -> ModelProfile:
    """Return supported profile by name, defaulting to deterministic 8gb preset."""

    normalized = (name or "8gb").strip().lower()
    if normalized == "16gb":
        return _PROFILE_16GB
    return _PROFILE_8GB


def clone_profile_with_model_name(profile: ModelProfile, model_name: str | None) -> ModelProfile:
    """Return a profile clone with model_name override when provided."""

    normalized = (model_name or "").strip()
    if not normalized:
        return profile
    return replace(profile, model_name=normalized)


class InferenceClient(Protocol):
    """Interface for generating dual twin responses from local inputs."""

    def generate_dual_response(
        self,
        user_text: str,
        grounding: GroundingMetadata,
        model_profile: ModelProfile,
    ) -> tuple[str, str]:
        """Generate supportive and honest responses."""


class LocalHeuristicClient:
    """Deterministic in-process fallback used across tests and offline runs."""

    def generate_dual_response(
        self,
        user_text: str,
        grounding: GroundingMetadata,
        model_profile: ModelProfile,
    ) -> tuple[str, str]:
        del model_profile
        cleaned_text = (user_text or "").strip() or "that"
        supportive = self._build_supportive_response(cleaned_text, grounding)
        honest = self._build_honest_response(cleaned_text, grounding)
        return supportive, honest

    def _build_supportive_response(self, user_text: str, grounding: GroundingMetadata) -> str:
        base = f"You are moving in the right direction with {user_text}."
        if grounding.profile_tone:
            base += (
                f" I will match your preferred {grounding.profile_tone} tone "
                "while helping you plan the next step."
            )
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


class OllamaClient:
    """Local ollama CLI-backed runtime client."""

    def __init__(self, command_runner: Callable[..., CompletedProcess[str]] | None = None) -> None:
        self._command_runner = command_runner or run

    def generate_dual_response(
        self,
        user_text: str,
        grounding: GroundingMetadata,
        model_profile: ModelProfile,
    ) -> tuple[str, str]:
        cleaned_text = (user_text or "").strip() or "that"

        supportive_prompt = self._build_prompt("supportive", cleaned_text, grounding)
        honest_prompt = self._build_prompt("honest", cleaned_text, grounding)

        supportive = self._run_ollama(model_profile, supportive_prompt)
        honest = self._run_ollama(model_profile, honest_prompt)

        if not supportive or not honest:
            raise RuntimeError("ollama returned an empty response")

        return supportive, honest

    def _build_prompt(self, voice: str, user_text: str, grounding: GroundingMetadata) -> str:
        hint_text = grounding.hints[0] if grounding.hints else "none"
        tone_text = grounding.profile_tone or "practical"

        return (
            "You are generating a single short planning response. "
            "Keep it to 2-4 sentences and deterministic. "
            f"Voice={voice}. UserText={user_text}. GroundingHint={hint_text}. "
            f"ProfileTone={tone_text}."
        )

    def _run_ollama(self, model_profile: ModelProfile, prompt: str) -> str:
        # Temperature 0 keeps local model behavior stable for repeat runs.
        command = [
            "ollama",
            "run",
            model_profile.model_name,
            prompt,
        ]
        env = None

        try:
            result = self._command_runner(
                command,
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
        except FileNotFoundError as exc:
            raise RuntimeError("ollama CLI not found on PATH") from exc
        except CalledProcessError as exc:
            stderr = (exc.stderr or "").strip()
            stdout = (exc.stdout or "").strip()
            message = stderr or stdout or str(exc)
            raise RuntimeError(f"ollama runtime failed: {message}") from exc

        return (result.stdout or "").strip()
