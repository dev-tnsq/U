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
from u_core.reflection import PlannerExecutionOutcome, apply_execution_reflection


class TestReflectionEngine(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "memory.db"
        self.schema_path = ROOT / "src" / "u_core" / "memory" / "schema.sql"
        self.store = SQLiteStore(self.db_path, self.schema_path)
        self.store.initialize()
        self.profile_store = ProfileStore(self.store)
        self.graph_store = GraphStore(self.store)

    def tearDown(self) -> None:
        self.store.close()
        self.tmp_dir.cleanup()

    def test_apply_execution_reflection_writes_reflection_profile_and_edges(self) -> None:
        outcome = PlannerExecutionOutcome(
            goal="Ship parser module",
            executed=True,
            actions=["write parser", "add tests"],
            results=["ok", "ok"],
            success=True,
            reviewer="u",
            tags=["release", "quality"],
            profile_updates={"tone": "concise"},
        )

        result = apply_execution_reflection(
            self.store,
            outcome,
            profile_store=self.profile_store,
            graph_store=self.graph_store,
        )

        self.assertIsNotNone(result.reflection.id)
        self.assertEqual("planner_execution", result.reflection.kind)
        self.assertIn("status succeeded", result.reflection.content)
        self.assertEqual(3, result.edge_count)

        profile = self.profile_store.load_profile()
        self.assertIsNotNone(profile)
        assert profile is not None
        self.assertEqual("concise", profile.data["tone"])
        self.assertEqual("succeeded", profile.data["last_execution_status"])
        self.assertEqual("Ship parser module", profile.data["recent_goals"][0])

        completed_edges = self.graph_store.list_edges(source="planner", relation="completed")
        self.assertEqual(1, len(completed_edges))
        self.assertEqual("goal:ship-parser-module", completed_edges[0].target)

    def test_apply_execution_reflection_not_executed_sets_planned_relation(self) -> None:
        outcome = PlannerExecutionOutcome(
            goal="Draft docs",
            executed=False,
            actions=["outline"],
            results=[],
            success=None,
            tags=["docs"],
        )

        apply_execution_reflection(
            self.store,
            outcome,
            profile_store=self.profile_store,
            graph_store=self.graph_store,
        )

        planned_edges = self.graph_store.list_edges(source="planner", relation="planned")
        self.assertEqual(1, len(planned_edges))
        self.assertEqual("goal:draft-docs", planned_edges[0].target)


if __name__ == "__main__":
    unittest.main()
