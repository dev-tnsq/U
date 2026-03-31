from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from u_core.twin import TwinContext, TwinReasoningEngine, get_model_profile
from u_core.twin.runtime_client import (
    GroundingMetadata,
    LocalHeuristicClient,
    OllamaClient,
    clone_profile_with_model_name,
)


class _FailingClient:
    def generate_dual_response(
        self,
        user_text: str,
        grounding: GroundingMetadata,
        model_profile,
    ) -> tuple[str, str]:
        del user_text, grounding, model_profile
        raise RuntimeError("runtime unavailable")


class TestRuntimeClientProfiles(unittest.TestCase):
    def test_profile_defaults_to_8gb(self) -> None:
        profile = get_model_profile(None)

        self.assertEqual("8gb", profile.name)
        self.assertEqual("llama3.2:3b", profile.model_name)

    def test_profile_16gb_is_supported(self) -> None:
        profile = get_model_profile("16GB")

        self.assertEqual("16gb", profile.name)
        self.assertEqual("llama3.1:8b", profile.model_name)

    def test_clone_profile_with_model_name_overrides_when_present(self) -> None:
        base_profile = get_model_profile("8gb")

        overridden = clone_profile_with_model_name(base_profile, "qwen2.5:7b")

        self.assertEqual("qwen2.5:7b", overridden.model_name)
        self.assertEqual(base_profile.context_window, overridden.context_window)

    def test_clone_profile_with_model_name_ignores_empty_override(self) -> None:
        base_profile = get_model_profile("16gb")

        same = clone_profile_with_model_name(base_profile, "   ")

        self.assertIs(base_profile, same)


class TestRuntimeClientBehavior(unittest.TestCase):
    def test_local_heuristic_client_is_deterministic(self) -> None:
        client = LocalHeuristicClient()
        grounding = GroundingMetadata(hints=["recent tags include focus"], tags_used=["focus"])

        first = client.generate_dual_response("I need a plan", grounding, get_model_profile("8gb"))
        second = client.generate_dual_response("I need a plan", grounding, get_model_profile("8gb"))

        self.assertEqual(first, second)

    def test_engine_raises_in_strict_mode_when_runtime_fails(self) -> None:
        engine = TwinReasoningEngine(
            inference_client=_FailingClient(),
            model_profile=get_model_profile("16gb"),
        )

        with self.assertRaisesRegex(
            RuntimeError,
            "Twin runtime inference failed and strict_runtime=True",
        ):
            engine.generate_dual_response("", TwinContext())

    def test_engine_falls_back_in_non_strict_mode_when_runtime_fails(self) -> None:
        engine = TwinReasoningEngine(
            inference_client=_FailingClient(),
            model_profile=get_model_profile("16gb"),
            strict_runtime=False,
        )

        response = engine.generate_dual_response("", TwinContext())

        self.assertIn("that", response.supportive_response)
        self.assertIn("limited prior memory", response.honest_response)

    def test_ollama_client_returns_clear_error_if_binary_missing(self) -> None:
        def missing_binary(*args, **kwargs):
            del args, kwargs
            raise FileNotFoundError("ollama not installed")

        client = OllamaClient(command_runner=missing_binary)

        with self.assertRaisesRegex(RuntimeError, "ollama CLI not found"):
            client.generate_dual_response(
                "Plan sprint",
                GroundingMetadata(),
                get_model_profile("8gb"),
            )


if __name__ == "__main__":
    unittest.main()
