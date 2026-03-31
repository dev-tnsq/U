from __future__ import annotations

import argparse
from datetime import datetime, timezone
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from u_core.agent.policy import (
    AgentPolicy,
    DEFAULT_ALLOWED_SCOPES,
    policy_path,
    save_policy,
)


def _parse_bool(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"true", "1", "yes", "y"}:
        return True
    if normalized in {"false", "0", "no", "n"}:
        return False
    raise argparse.ArgumentTypeError("Expected true/false value.")


def _parse_scopes(raw_scopes: str | None) -> list[str]:
    if raw_scopes is None:
        return list(DEFAULT_ALLOWED_SCOPES)
    scopes = [scope.strip() for scope in raw_scopes.split(",") if scope.strip()]
    return scopes or list(DEFAULT_ALLOWED_SCOPES)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Grant local runtime consent for U.")
    parser.add_argument(
        "--granted-by",
        required=True,
        help="Name or identifier of the person granting consent.",
    )
    parser.add_argument(
        "--scopes",
        default=None,
        help="Optional comma-separated list of allowed scopes.",
    )
    parser.add_argument(
        "--monitor-enabled",
        type=_parse_bool,
        default=None,
        help="Optional monitor mode toggle (true/false).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    scopes = _parse_scopes(args.scopes)
    monitor_enabled = args.monitor_enabled if args.monitor_enabled is not None else False

    policy = AgentPolicy(
        consent_granted=True,
        allowed_scopes=scopes,
        monitor_enabled=monitor_enabled,
        allow_network=False,
        reversible_actions_only=True,
        granted_at=datetime.now(timezone.utc).isoformat(),
        granted_by=args.granted_by,
    )
    target = save_policy(policy, path=policy_path())

    print(f"Consent granted policy written to: {target}")
    print(f"Allowed scopes: {', '.join(scopes)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
