"""Planner runtime skeleton for preview, approval, and execution flow."""

from __future__ import annotations

import json
from typing import Protocol

from u_core.memory import SQLiteStore
from u_core.reflection import PlannerExecutionOutcome, apply_execution_reflection

from .schemas import PlannerApproval, PlannerExecutionEnvelope, PlannerPreview, TrustLevel
from .tools import ToolRegistry


class ActionExecutor(Protocol):
    """Protocol for executing a single planner action."""

    def execute(self, action: str) -> str:
        """Execute one action and return a textual result."""


class PlannerRuntime:
    """Minimal runtime that enforces planner execution gates."""

    def __init__(
        self,
        executor: ActionExecutor | None = None,
        tool_registry: ToolRegistry | None = None,
    ) -> None:
        self.executor = executor
        self.tool_registry = tool_registry

    def _parse_tool_action(self, action: str) -> tuple[str, dict[str, object]] | None:
        """Parse tool action text and return (name, payload) when applicable."""
        if not action.startswith("tool:"):
            return None
        try:
            _, tool_name, payload_raw = action.split(":", 2)
        except ValueError as err:
            raise ValueError(f"invalid tool action format: {action}") from err
        try:
            payload = json.loads(payload_raw)
        except json.JSONDecodeError as err:
            raise ValueError(f"invalid tool payload JSON for action: {action}") from err
        if not isinstance(payload, dict):
            raise ValueError(f"tool payload must be a JSON object for action: {action}")
        return tool_name, payload

    def _enforce_tool_approval(
        self,
        tool_action: str,
        envelope: PlannerExecutionEnvelope,
    ) -> None:
        """Require explicit confirm token for irreversible tool actions."""
        parsed = self._parse_tool_action(tool_action)
        if parsed is None:
            return
        if self.tool_registry is None:
            raise ValueError("tool action received but no tool registry is configured")
        tool_name, _ = parsed
        tool = self.tool_registry.get(tool_name)
        if tool.risk != "irreversible_write":
            return
        reason = "" if envelope.approval is None or envelope.approval.reason is None else envelope.approval.reason
        if "CONFIRM" not in reason:
            raise PermissionError(
                f"irreversible tool requires approval reason with CONFIRM token: {tool_name}"
            )

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
            for action in envelope.preview.proposed_actions:
                self._enforce_tool_approval(action, envelope)
                parsed = self._parse_tool_action(action)
                if parsed is not None:
                    if self.tool_registry is None:
                        raise ValueError("tool action received but no tool registry is configured")
                    tool_name, payload = parsed
                    results.append(self.tool_registry.execute(tool_name, payload))
                    continue
                if self.executor is not None:
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