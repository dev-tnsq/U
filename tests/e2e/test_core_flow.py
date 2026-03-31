from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from u_core.agent import PlannerRuntime
from u_core.ingest import ingest_records, parse_local_notes
from u_core.memory import SQLiteStore
from u_core.twin import TwinReasoningEngine, build_twin_context


class _DeterministicExecutor:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def execute(self, action: str) -> str:
        self.calls.append(action)
        return f"done:{action}"


class TestCoreEndToEndFlow(unittest.TestCase):
    def test_ingest_to_twin_to_runtime_execution_persists_reflection(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "memory.db"
            schema_path = ROOT / "src" / "u_core" / "memory" / "schema.sql"
            store = SQLiteStore(db_path, schema_path)
            store.initialize()

            try:
                records = parse_local_notes(
                    """
                    - Ship parser tests #quality
                    - Keep sprint scope small #focus
                    """
                )
                events = ingest_records(store, records, event_type="ingest.local_notes")
                self.assertEqual(2, len(events))

                persisted_events = store.list_events(limit=10, event_type="ingest.local_notes")
                self.assertEqual(2, len(persisted_events))

                context = build_twin_context(store)
                self.assertGreaterEqual(len(context.recent_events), 2)
                self.assertIn("quality", context.tags)
                self.assertIn("focus", context.tags)

                twin_engine = TwinReasoningEngine()
                twin_response = twin_engine.generate_dual_response(
                    "How should I execute this plan this week?",
                    context,
                )
                self.assertTrue(twin_response.supportive_response.strip())
                self.assertTrue(twin_response.honest_response.strip())
                self.assertIsNotNone(twin_response.grounding)

                executor = _DeterministicExecutor()
                runtime = PlannerRuntime(executor)
                envelope = runtime.create_envelope(
                    "Execute top two tasks",
                    proposed_actions=[
                        "confirm priorities from twin context",
                        "run focused implementation block",
                    ],
                    trust_level="execute-approved",
                )
                runtime.apply_approval(envelope, approved=True, reviewer="u")

                results = runtime.execute(envelope, store=store)

                self.assertEqual(
                    [
                        "confirm priorities from twin context",
                        "run focused implementation block",
                    ],
                    executor.calls,
                )
                self.assertEqual(
                    [
                        "done:confirm priorities from twin context",
                        "done:run focused implementation block",
                    ],
                    results,
                )
                self.assertTrue(envelope.executed)

                reflections = store.list_reflections(limit=10, kind="planner_execution")
                self.assertEqual(1, len(reflections))
                self.assertEqual("Execute top two tasks", reflections[0].metadata["goal"])
                self.assertTrue(reflections[0].metadata["executed"])
                self.assertTrue(reflections[0].metadata["success"])
                self.assertEqual("u", reflections[0].metadata["reviewer"])
            finally:
                store.close()


if __name__ == "__main__":
    unittest.main()