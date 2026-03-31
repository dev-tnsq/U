from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from u_core.twin.benchmark import (
    aggregate_model_score,
    build_prompt_benchmark,
    parse_model_size_billions,
    prompt_suite,
    recommend_profile_for_model,
    score_quality,
    select_best_model,
)


class TestBenchmarkHeuristics(unittest.TestCase):
    def test_prompt_suite_is_fixed_and_non_empty(self) -> None:
        prompts = prompt_suite()

        self.assertGreaterEqual(len(prompts), 3)
        self.assertEqual(prompts, prompt_suite())

    def test_parse_model_size_billions_handles_common_names(self) -> None:
        self.assertEqual(3.0, parse_model_size_billions("llama3.2:3b"))
        self.assertEqual(8.0, parse_model_size_billions("qwen2.5:8b-instruct"))
        self.assertIsNone(parse_model_size_billions("phi4-mini"))

    def test_recommend_profile_for_model_uses_size_threshold(self) -> None:
        self.assertEqual("8gb", recommend_profile_for_model("llama3.2:3b"))
        self.assertEqual("16gb", recommend_profile_for_model("llama3.1:8b"))
        self.assertEqual("8gb", recommend_profile_for_model("custom-local-model"))

    def test_quality_scoring_prefers_actionable_responses(self) -> None:
        high = score_quality(
            "Start with a 20 minute reliability audit, then pick one failing endpoint. "
            "Measure error rate before and after the fix, and document the tradeoff."
        )
        low = score_quality("ok")

        self.assertGreater(high, low)
        self.assertGreaterEqual(high, 0.5)


class TestBenchmarkAggregation(unittest.TestCase):
    def test_aggregate_and_recommend_best_model(self) -> None:
        fast_prompt = build_prompt_benchmark(
            "Prompt A",
            "Define a plan, pick the next step, and measure results after one action.",
            latency_ms=900,
        )
        steady_prompt = build_prompt_benchmark(
            "Prompt B",
            "Focus on one tradeoff, decide quickly, and execute the first step.",
            latency_ms=1200,
        )
        slow_prompt = build_prompt_benchmark(
            "Prompt A",
            "Do something.",
            latency_ms=6500,
        )

        fast_model = aggregate_model_score("llama3.2:3b", [fast_prompt, steady_prompt])
        slow_model = aggregate_model_score("llama3.1:8b", [slow_prompt])
        best = select_best_model([slow_model, fast_model])

        self.assertIsNotNone(best)
        assert best is not None
        self.assertEqual("llama3.2:3b", best.model_name)
        self.assertEqual("8gb", best.recommended_profile)


if __name__ == "__main__":
    unittest.main()
