from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from u_core.memory import GraphStore, ProfileStore, SQLiteStore
from u_core.twin import TwinContext, TwinReasoningEngine, build_twin_context


class _FailingClient:
    def generate_dual_response(self, user_text, grounding, model_profile):
        del user_text, grounding, model_profile
        raise RuntimeError("runtime unavailable")


class TestTwinReasoningEngine(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = TwinReasoningEngine()

    def test_returns_both_voices_always(self) -> None:
        response = self.engine.generate_dual_response("I need a plan", TwinContext())

        self.assertIsInstance(response.supportive_response, str)
        self.assertIsInstance(response.honest_response, str)

    def test_supportive_and_honest_are_not_empty(self) -> None:
        response = self.engine.generate_dual_response("How do I focus?", TwinContext())

        self.assertTrue(response.supportive_response.strip())
        self.assertTrue(response.honest_response.strip())

    def test_fallback_behavior_with_empty_context(self) -> None:
        response = self.engine.generate_dual_response("", TwinContext())

        self.assertIn("that", response.supportive_response)
        self.assertIn("limited prior memory", response.honest_response)
        self.assertIsNone(response.grounding)

    def test_memory_rich_context_contains_grounding_hint(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "memory.db"
            schema_path = ROOT / "src" / "u_core" / "memory" / "schema.sql"
            store = SQLiteStore(db_path, schema_path)
            store.initialize()

            store.create_event(
                "action",
                "Completed a sprint task",
                {"tags": ["focus", "execution"], "outcome": "finished sprint"},
            )
            store.create_reflection(
                "summary",
                "Delivery was smoother after removing scope",
                {"outcomes": ["clear scope"]},
            )

            profile_store = ProfileStore(store)
            profile_store.update_profile({"tone": "concise", "goals": ["ship weekly"]})

            graph_store = GraphStore(store)
            graph_store.upsert_edge(
                "u",
                "weekly-shipping",
                "supports",
                metadata={"tags": ["cadence"]},
            )

            context = build_twin_context(
                store,
                profile_store=profile_store,
                graph_store=graph_store,
            )
            response = self.engine.generate_dual_response("What should I do this week?", context)

            grounding = response.grounding
            self.assertIsNotNone(grounding)
            assert grounding is not None
            self.assertTrue(grounding.hints)
            self.assertTrue(
                grounding.tags_used
                or grounding.outcomes_used
                or bool(grounding.profile_tone)

            )

            store.close()

    def test_name_query_resolves_from_profile_snapshot_name(self) -> None:
        context = TwinContext(profile_snapshot={"name": "Tanishq"})

        response = self.engine.generate_dual_response("what is my name", context)

        self.assertIn("Tanishq", response.supportive_response)
        self.assertIn("Tanishq", response.honest_response)

    def test_name_query_resolves_from_users_path_metadata(self) -> None:
        context = TwinContext(
            recent_events=[
                {
                    "metadata": {
                        "path": "/Users/tanishqmaheshwari/code/U/notes/todo.md",
                    }
                }
            ]
        )

        response = self.engine.generate_dual_response("who am i", context)

        self.assertIn("tanishqmaheshwari", response.supportive_response)
        self.assertIn("tanishqmaheshwari", response.honest_response)

    def test_name_query_unknown_returns_local_memory_message(self) -> None:
        response = self.engine.generate_dual_response("my name", TwinContext())

        self.assertIn("not yet in local memory", response.supportive_response.lower())
        self.assertIn("not yet in local memory", response.honest_response.lower())

    def test_name_query_is_deterministic_even_if_inference_client_fails(self) -> None:
        engine = TwinReasoningEngine(inference_client=_FailingClient(), strict_runtime=True)
        context = TwinContext(profile_snapshot={"name": "Tanishq"})

        response = engine.generate_dual_response("what is my name", context)

        self.assertIn("Tanishq", response.supportive_response)
        self.assertIn("Tanishq", response.honest_response)


if __name__ == "__main__":
    unittest.main()
