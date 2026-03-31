from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from u_app.gradio_app import (
    _resolve_profile_name,
    _resolve_runtime_name,
    build_planner_runtime,
    build_planner_preview,
    generate_dual_outputs,
)
from u_core.twin import TwinContext


class TestGradioAppHelpers(unittest.TestCase):
    def test_build_planner_runtime_includes_default_macos_tools(self) -> None:
        runtime = build_planner_runtime()

        self.assertIsNotNone(runtime.tool_registry)
        assert runtime.tool_registry is not None
        names = [tool.name for tool in runtime.tool_registry.list_tools()]
        self.assertEqual(
            ["app_open_preview", "calendar_draft_event", "file_search"],
            names,
        )

    def test_runtime_name_parser_defaults_and_validates(self) -> None:
        self.assertEqual("heuristic", _resolve_runtime_name(None))
        self.assertEqual("heuristic", _resolve_runtime_name("unknown"))
        self.assertEqual("ollama", _resolve_runtime_name("OLLAMA"))

    def test_profile_name_parser_defaults_and_validates(self) -> None:
        self.assertEqual("8gb", _resolve_profile_name(None))
        self.assertEqual("8gb", _resolve_profile_name("24gb"))
        self.assertEqual("16gb", _resolve_profile_name("16GB"))

    def test_planner_preview_uses_fallback_goal_for_empty_input(self) -> None:
        goal, actions = build_planner_preview("", TwinContext())

        self.assertEqual(goal, "Clarify the immediate next step")
        self.assertIn("Define one 25-minute action", actions)

    def test_planner_preview_uses_context_signals(self) -> None:
        context = TwinContext(tags=["focus"], outcomes=["daily planning"])
        goal, actions = build_planner_preview("Ship MVP", context)

        self.assertEqual(goal, "Ship MVP")
        self.assertIn("Prioritize work tagged: focus.", actions)
        self.assertIn("Reuse prior winning pattern: daily planning.", actions)

    def test_generate_dual_outputs_returns_all_panels(self) -> None:
        context = TwinContext(tags=["execution"])

        supportive, honest, goal, actions = generate_dual_outputs("Close open loop", context)

        self.assertTrue(supportive.strip())
        self.assertTrue(honest.strip())
        self.assertEqual(goal, "Close open loop")
        self.assertIn("- ", actions)


if __name__ == "__main__":
    unittest.main()
