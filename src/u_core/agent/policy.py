"""Local consent policy management for privacy-first runtime enforcement."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
import json

DEFAULT_ALLOWED_SCOPES: list[str] = [
    "memory:read",
    "memory:write",
    "planner:preview",
    "tools:local_safe",
]


@dataclass
class AgentPolicy:
    consent_granted: bool
    allowed_scopes: list[str] = field(default_factory=lambda: list(DEFAULT_ALLOWED_SCOPES))
    monitor_enabled: bool = False
    allow_network: bool = False
    reversible_actions_only: bool = True
    granted_at: str | None = None
    granted_by: str | None = None


def default_policy() -> AgentPolicy:
    return AgentPolicy(
        consent_granted=False,
        allowed_scopes=list(DEFAULT_ALLOWED_SCOPES),
        monitor_enabled=False,
        allow_network=False,
        reversible_actions_only=True,
        granted_at=None,
        granted_by=None,
    )


def _primary_data_root() -> Path:
    return Path.home() / "Library" / "Application Support" / "U"


def _fallback_data_root() -> Path:
    return Path.home() / "U" / "data"


def policy_path(data_root: Path | None = None) -> Path:
    if data_root is not None:
        target = data_root / "runtime" / "policy.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        return target

    primary = _primary_data_root() / "runtime" / "policy.json"
    fallback = _fallback_data_root() / "runtime" / "policy.json"

    try:
        primary.parent.mkdir(parents=True, exist_ok=True)
        return primary
    except OSError:
        fallback.parent.mkdir(parents=True, exist_ok=True)
        return fallback


def save_policy(policy: AgentPolicy, path: Path | None = None) -> Path:
    target = path or policy_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(asdict(policy), indent=2), encoding="utf-8")
    return target


def load_policy(path: Path | None = None) -> AgentPolicy:
    target = path or policy_path()
    if not target.exists():
        policy = default_policy()
        save_policy(policy, target)
        return policy

    payload = json.loads(target.read_text(encoding="utf-8"))
    return AgentPolicy(
        consent_granted=bool(payload.get("consent_granted", False)),
        allowed_scopes=list(payload.get("allowed_scopes") or list(DEFAULT_ALLOWED_SCOPES)),
        monitor_enabled=bool(payload.get("monitor_enabled", False)),
        allow_network=bool(payload.get("allow_network", False)),
        reversible_actions_only=bool(payload.get("reversible_actions_only", True)),
        granted_at=payload.get("granted_at"),
        granted_by=payload.get("granted_by"),
    )


def ensure_policy_allows_runtime(policy: AgentPolicy) -> None:
    if not policy.consent_granted:
        raise RuntimeError("Local consent is required before runtime operations are allowed.")
    if policy.allow_network:
        raise RuntimeError("Policy violation: network access must remain disabled for local runtime.")
