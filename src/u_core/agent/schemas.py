"""Typed planner schemas for preview, approval, and execution envelopes."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

TrustLevel = Literal["read-only", "draft-only", "execute-approved"]
ExecutionPhase = Literal["preview", "approve", "execute", "verify"]


@dataclass
class PlannerPreview:
    """Planner proposal shown to the user before any execution."""

    goal: str
    proposed_actions: list[str] = field(default_factory=list)
    safety_notes: list[str] = field(default_factory=list)


@dataclass
class PlannerApproval:
    """Human approval record required before executable actions."""

    approved: bool
    reviewer: str | None = None
    reason: str | None = None


@dataclass
class PlannerExecutionEnvelope:
    """Execution envelope enforcing preview and approval gating rules."""

    preview: PlannerPreview
    approval: PlannerApproval | None = None
    trust_level: TrustLevel = "read-only"
    executed: bool = False

    def is_execution_permitted(self) -> bool:
        """Return true only when trust level and approval both allow execution."""
        return (
            self.trust_level == "execute-approved"
            and self.approval is not None
            and self.approval.approved
        )

    def current_phase(self) -> ExecutionPhase:
        """Return the current workflow phase in Preview -> Approve -> Execute -> Verify."""
        if self.executed:
            return "verify"
        if self.approval is None:
            return "preview"
        if not self.approval.approved:
            return "approve"
        return "execute"
