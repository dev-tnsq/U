from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from u_core.agent import RegisteredTool, ToolRegistry


class TestToolRegistry(unittest.TestCase):
    def test_register_get_list_execute(self) -> None:
        registry = ToolRegistry()

        def _handler(payload: dict[str, object]) -> str:
            return f"ok:{payload['query']}"

        registry.register(
            RegisteredTool(
                name="file_search",
                risk="read_only",
                handler=_handler,
                description="Search files",
            )
        )

        tool = registry.get("file_search")
        listed = registry.list_tools()
        result = registry.execute("file_search", {"query": "notes"})

        self.assertEqual("file_search", tool.name)
        self.assertEqual(["file_search"], [entry.name for entry in listed])
        self.assertEqual("ok:notes", result)

    def test_register_rejects_duplicate_names(self) -> None:
        registry = ToolRegistry()
        tool = RegisteredTool(
            name="write_note",
            risk="reversible_write",
            handler=lambda payload: "ok",
            description="Write note",
        )
        registry.register(tool)

        with self.assertRaises(ValueError):
            registry.register(tool)

    def test_get_unknown_tool_has_clear_error(self) -> None:
        registry = ToolRegistry()

        with self.assertRaisesRegex(KeyError, "unknown tool: missing_tool"):
            registry.get("missing_tool")


if __name__ == "__main__":
    unittest.main()
