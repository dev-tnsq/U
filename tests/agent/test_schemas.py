from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from u_core.agent import PlannerApproval, PlannerExecutionEnvelope, PlannerPreview


class TestPlannerExecutionEnvelope(unittest.TestCase):
    def test_defaults_to_preview_and_blocks_execution(self) -> None:
        envelope = PlannerExecutionEnvelope(preview=PlannerPreview(goal="Ship phase 2"))

        self.assertEqual("preview", envelope.current_phase())
        self.assertFalse(envelope.is_execution_permitted())

    def test_rejected_approval_is_still_not_executable(self) -> None:
        envelope = PlannerExecutionEnvelope(
            preview=PlannerPreview(goal="Refactor planner"),
            approval=PlannerApproval(approved=False, reviewer="u", reason="missing risk notes"),
            trust_level="execute-approved",
        )

        self.assertEqual("approve", envelope.current_phase())
        self.assertFalse(envelope.is_execution_permitted())

    def test_execution_requires_execute_approved_trust(self) -> None:
        approved = PlannerApproval(approved=True, reviewer="u")
        envelope = PlannerExecutionEnvelope(
            preview=PlannerPreview(goal="Run safe tool action"),
            approval=approved,
            trust_level="draft-only",
        )

        self.assertEqual("execute", envelope.current_phase())
        self.assertFalse(envelope.is_execution_permitted())

    def test_execute_and_verify_phases(self) -> None:
        envelope = PlannerExecutionEnvelope(
            preview=PlannerPreview(goal="Commit approved change"),
            approval=PlannerApproval(approved=True, reviewer="u"),
            trust_level="execute-approved",
        )

        self.assertEqual("execute", envelope.current_phase())
        self.assertTrue(envelope.is_execution_permitted())

        envelope.executed = True
        self.assertEqual("verify", envelope.current_phase())


if __name__ == "__main__":
    unittest.main()
