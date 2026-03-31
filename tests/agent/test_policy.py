from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from u_core.agent.policy import (
    AgentPolicy,
    DEFAULT_ALLOWED_SCOPES,
    default_policy,
    ensure_policy_allows_runtime,
    load_policy,
    policy_path,
    save_policy,
)


class TestAgentPolicy(unittest.TestCase):
    def test_default_allowed_scopes_include_device_apps_and_settings(self) -> None:
        self.assertIn("device:read", DEFAULT_ALLOWED_SCOPES)
        self.assertIn("apps:read", DEFAULT_ALLOWED_SCOPES)
        self.assertIn("settings:read", DEFAULT_ALLOWED_SCOPES)

    def test_default_policy_has_safe_defaults(self) -> None:
        policy = default_policy()

        self.assertFalse(policy.consent_granted)
        self.assertEqual(DEFAULT_ALLOWED_SCOPES, policy.allowed_scopes)
        self.assertFalse(policy.monitor_enabled)
        self.assertFalse(policy.allow_network)
        self.assertTrue(policy.reversible_actions_only)
        self.assertIsNone(policy.granted_at)
        self.assertIsNone(policy.granted_by)

    def test_policy_path_uses_data_root_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            target = policy_path(data_root=root)

            self.assertEqual(root / "runtime" / "policy.json", target)
            self.assertTrue((root / "runtime").exists())

    def test_load_policy_creates_default_file_if_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            target = Path(tmp_dir) / "runtime" / "policy.json"

            policy = load_policy(path=target)

            self.assertTrue(target.exists())
            self.assertFalse(policy.consent_granted)
            payload = json.loads(target.read_text(encoding="utf-8"))
            self.assertFalse(payload["consent_granted"])

    def test_save_and_load_policy_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            target = Path(tmp_dir) / "runtime" / "policy.json"
            written = AgentPolicy(
                consent_granted=True,
                allowed_scopes=["memory:read", "memory:write"],
                monitor_enabled=True,
                allow_network=False,
                reversible_actions_only=True,
                granted_at="2026-04-01T00:00:00+00:00",
                granted_by="tester",
            )

            save_policy(written, path=target)
            loaded = load_policy(path=target)

            self.assertEqual(written, loaded)

    def test_enforcement_rejects_missing_consent(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "consent"):
            ensure_policy_allows_runtime(default_policy())

    def test_enforcement_rejects_network_enabled(self) -> None:
        policy = AgentPolicy(
            consent_granted=True,
            allowed_scopes=list(DEFAULT_ALLOWED_SCOPES),
            monitor_enabled=False,
            allow_network=True,
            reversible_actions_only=True,
            granted_at="2026-04-01T00:00:00+00:00",
            granted_by="tester",
        )

        with self.assertRaisesRegex(RuntimeError, "network"):
            ensure_policy_allows_runtime(policy)

    def test_enforcement_allows_safe_granted_policy(self) -> None:
        policy = AgentPolicy(
            consent_granted=True,
            allowed_scopes=list(DEFAULT_ALLOWED_SCOPES),
            monitor_enabled=False,
            allow_network=False,
            reversible_actions_only=True,
            granted_at="2026-04-01T00:00:00+00:00",
            granted_by="tester",
        )

        ensure_policy_allows_runtime(policy)


if __name__ == "__main__":
    unittest.main()
