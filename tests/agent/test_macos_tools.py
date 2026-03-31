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

from u_core.agent import (
    build_default_macos_tool_registry,
    handle_app_open_preview,
    handle_calendar_draft_event,
    handle_file_search,
)


class TestMacOSTools(unittest.TestCase):
    def test_file_search_finds_matches_with_caps(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            (root / "a.txt").write_text("alpha\nneedle here\nomega\n", encoding="utf-8")
            (root / "b.txt").write_text("needle again\n", encoding="utf-8")

            raw = handle_file_search(
                {
                    "query": "needle",
                    "root_path": str(root),
                    "max_files": 2,
                    "max_matches": 1,
                }
            )
            parsed = json.loads(raw)

            self.assertEqual("ok", parsed["status"])
            self.assertEqual("file_search", parsed["tool"])
            self.assertEqual(1, len(parsed["matches"]))
            self.assertTrue(parsed["truncated"])

    def test_file_search_rejects_empty_query(self) -> None:
        raw = handle_file_search({"query": "  ", "root_path": "."})
        parsed = json.loads(raw)

        self.assertEqual("invalid_payload", parsed["status"])
        self.assertIn("non-empty", parsed["reason"])

    def test_app_open_preview_returns_preview_only_payload(self) -> None:
        raw = handle_app_open_preview(
            {"app_name": "Preview", "args": ["/tmp/example.pdf"]}
        )
        parsed = json.loads(raw)

        self.assertEqual("app_open_preview", parsed["tool"])
        self.assertEqual("preview_only", parsed["status"])
        self.assertFalse(parsed["will_execute"])
        self.assertEqual("Preview", parsed["action"]["app_name"])

    def test_calendar_draft_event_returns_stable_draft(self) -> None:
        payload = {
            "title": "Project Review",
            "starts_at": "2026-04-01T10:00:00",
            "ends_at": "2026-04-01T10:30:00",
            "location": "Office",
            "notes": "Agenda prep",
        }
        first = json.loads(handle_calendar_draft_event(payload))
        second = json.loads(handle_calendar_draft_event(payload))

        self.assertEqual("calendar_draft_event", first["tool"])
        self.assertEqual("draft", first["status"])
        self.assertEqual(first["draft_id"], second["draft_id"])
        self.assertEqual("Project Review", first["event"]["title"])

    def test_default_registry_contains_expected_tools_and_risks(self) -> None:
        registry = build_default_macos_tool_registry()

        entries = {tool.name: tool.risk for tool in registry.list_tools()}
        self.assertEqual(
            {
                "app_open_preview": "reversible_write",
                "calendar_draft_event": "reversible_write",
                "file_search": "read_only",
            },
            entries,
        )
        self.assertNotIn("irreversible_write", set(entries.values()))


if __name__ == "__main__":
    unittest.main()
