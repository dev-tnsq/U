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
from u_core.agent import RegisteredTool, ToolRegistry
from u_core.memory import SQLiteStore


class _FakeExecutor:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def execute(self, action: str) -> str:
        self.calls.append(action)
        return f"done:{action}"


class TestPlannerRuntime(unittest.TestCase):
    def test_create_envelope_defaults_to_preview_phase(self) -> None:
        runtime = PlannerRuntime()

        envelope = runtime.create_envelope("Ship phase 3")

        self.assertEqual("preview", envelope.current_phase())
        self.assertFalse(envelope.is_execution_permitted())

    def test_execute_runs_actions_after_approval_and_trust(self) -> None:
        executor = _FakeExecutor()
        runtime = PlannerRuntime(executor)
        envelope = runtime.create_envelope(
            "Refactor module",
            proposed_actions=["collect context", "apply patch"],
            trust_level="execute-approved",
        )
        runtime.apply_approval(envelope, approved=True, reviewer="u")

        results = runtime.execute(envelope)

        self.assertEqual(["collect context", "apply patch"], executor.calls)
        self.assertEqual(["done:collect context", "done:apply patch"], results)
        self.assertEqual("verify", envelope.current_phase())

    def test_execute_raises_when_not_permitted(self) -> None:
        runtime = PlannerRuntime(_FakeExecutor())
        envelope = runtime.create_envelope(
            "Run action",
            proposed_actions=["unsafe action"],
            trust_level="draft-only",
        )
        runtime.apply_approval(envelope, approved=True, reviewer="u")

        with self.assertRaises(PermissionError):
            runtime.execute(envelope)

    def test_execute_without_executor_marks_complete(self) -> None:
        runtime = PlannerRuntime()
        envelope = runtime.create_envelope(
            "Record execution",
            proposed_actions=["noop"],
            trust_level="execute-approved",
        )
        runtime.apply_approval(envelope, approved=True, reviewer="u")

        results = runtime.execute(envelope)

        self.assertEqual([], results)
        self.assertTrue(envelope.executed)

    def test_execute_with_store_writes_planner_execution_reflection(self) -> None:
        executor = _FakeExecutor()
        runtime = PlannerRuntime(executor)
        envelope = runtime.create_envelope(
            "Ship parser",
            proposed_actions=["run tests"],
            trust_level="execute-approved",
        )
        runtime.apply_approval(envelope, approved=True, reviewer="u")

        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "memory.db"
            schema_path = ROOT / "src" / "u_core" / "memory" / "schema.sql"
            store = SQLiteStore(db_path, schema_path)
            store.initialize()
            try:
                runtime.execute(envelope, store=store)

                reflections = store.list_reflections(limit=10, kind="planner_execution")
                self.assertEqual(1, len(reflections))
                self.assertEqual("Ship parser", reflections[0].metadata["goal"])
                self.assertEqual(["run tests"], reflections[0].metadata["actions"])
                self.assertEqual(["done:run tests"], reflections[0].metadata["results"])
                self.assertTrue(reflections[0].metadata["executed"])
                self.assertTrue(reflections[0].metadata["success"])
            finally:
                store.close()

    def test_execute_runs_read_only_tool_with_approved_envelope(self) -> None:
        registry = ToolRegistry()
        registry.register(
            RegisteredTool(
                name="file_search",
                risk="read_only",
                handler=lambda payload: f"found:{payload['query']}",
                description="Search files",
            )
        )
        runtime = PlannerRuntime(tool_registry=registry)
        envelope = runtime.create_envelope(
            "Find notes",
            proposed_actions=['tool:file_search:{"query":"notes"}'],
            trust_level="execute-approved",
        )
        runtime.apply_approval(envelope, approved=True, reviewer="u", reason="approved")

        results = runtime.execute(envelope)

        self.assertEqual(["found:notes"], results)

    def test_irreversible_tool_fails_without_confirm_token(self) -> None:
        registry = ToolRegistry()
        registry.register(
            RegisteredTool(
                name="delete_note",
                risk="irreversible_write",
                handler=lambda payload: "deleted",
                description="Delete note",
            )
        )
        runtime = PlannerRuntime(tool_registry=registry)
        envelope = runtime.create_envelope(
            "Delete old note",
            proposed_actions=['tool:delete_note:{"id":"1"}'],
            trust_level="execute-approved",
        )
        runtime.apply_approval(envelope, approved=True, reviewer="u", reason="looks safe")

        with self.assertRaisesRegex(PermissionError, "CONFIRM"):
            runtime.execute(envelope)

    def test_irreversible_tool_executes_with_confirm_token(self) -> None:
        registry = ToolRegistry()
        registry.register(
            RegisteredTool(
                name="delete_note",
                risk="irreversible_write",
                handler=lambda payload: f"deleted:{payload['id']}",
                description="Delete note",
            )
        )
        runtime = PlannerRuntime(tool_registry=registry)
        envelope = runtime.create_envelope(
            "Delete old note",
            proposed_actions=['tool:delete_note:{"id":"1"}'],
            trust_level="execute-approved",
        )
        runtime.apply_approval(
            envelope,
            approved=True,
            reviewer="u",
            reason="CONFIRM remove stale note",
        )

        results = runtime.execute(envelope)

        self.assertEqual(["deleted:1"], results)


if __name__ == "__main__":
    unittest.main()