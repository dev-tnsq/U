"""Planner runtime skeleton for preview, approval, and execution flow."""

from __future__ import annotations

from typing import Protocol

from u_core.memory import SQLiteStore
from u_core.reflection import PlannerExecutionOutcome, apply_execution_reflection

from .schemas import PlannerApproval, PlannerExecutionEnvelope, PlannerPreview, TrustLevel


class ActionExecutor(Protocol):
    """Protocol for executing a single planner action."""

    def execute(self, action: str) -> str:
        """Execute one action and return a textual result."""


class PlannerRuntime:
    """Minimal runtime that enforces planner execution gates."""

    def __init__(self, executor: ActionExecutor | None = None) -> None:
        self.executor = executor

    def create_envelope(
        self,
        goal: str,
        *,
        proposed_actions: list[str] | None = None,
        safety_notes: list[str] | None = None,
        trust_level: TrustLevel = "read-only",
    ) -> PlannerExecutionEnvelope:
        preview = PlannerPreview(
            goal=goal,
            proposed_actions=proposed_actions or [],
            safety_notes=safety_notes or [],
        )
        return PlannerExecutionEnvelope(preview=preview, trust_level=trust_level)

    def apply_approval(
        self,
        envelope: PlannerExecutionEnvelope,
        *,
        approved: bool,
        reviewer: str | None = None,
        reason: str | None = None,
    ) -> PlannerExecutionEnvelope:
        envelope.approval = PlannerApproval(
            approved=approved,
            reviewer=reviewer,
            reason=reason,
        )
        return envelope

    def execute(
        self,
        envelope: PlannerExecutionEnvelope,
        *,
        store: SQLiteStore | None = None,
    ) -> list[str]:
        is_permitted = envelope.is_execution_permitted()
        if not is_permitted:
            if store is not None:
                apply_execution_reflection(
                    store,
                    PlannerExecutionOutcome(
                        goal=envelope.preview.goal,
                        executed=False,
                        actions=list(envelope.preview.proposed_actions),
                        results=[],
                        success=None,
                        reviewer=None if envelope.approval is None else envelope.approval.reviewer,
                    ),
                )
            raise PermissionError("execution requires approved envelope and execute-approved trust")

        results: list[str] = []
        execution_error: Exception | None = None
        try:
            if self.executor is not None:
                for action in envelope.preview.proposed_actions:
                    results.append(self.executor.execute(action))
        except Exception as err:
            execution_error = err
            raise
        finally:
            if store is not None:
                apply_execution_reflection(
                    store,
                    PlannerExecutionOutcome(
                        goal=envelope.preview.goal,
                        executed=True,
                        actions=list(envelope.preview.proposed_actions),
                        results=list(results),
                        success=execution_error is None,
                        reviewer=None if envelope.approval is None else envelope.approval.reviewer,
                    ),
                )

        envelope.executed = True
        return results