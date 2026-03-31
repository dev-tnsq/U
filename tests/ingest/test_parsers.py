from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from u_core.ingest import parse_local_notes, parse_telegram_export, parse_whatsapp_export


class TestIngestParsers(unittest.TestCase):
    def test_whatsapp_parser_extracts_messages_tags_and_metadata(self) -> None:
        raw = (
            "3/31/26, 9:41 PM - Alex: Ship update #release\n"
            "Next step is docs\n"
            "3/31/26, 9:42 PM - Sam: Ack #ops"
        )

        records = parse_whatsapp_export(raw)

        self.assertEqual(2, len(records))
        self.assertEqual("whatsapp", records[0].source)
        self.assertEqual(["release"], records[0].tags)
        self.assertIn("Next step is docs", records[0].content)
        self.assertEqual("Alex", records[0].metadata["sender"])

    def test_telegram_parser_supports_common_formats(self) -> None:
        raw = (
            "[31.03.26, 11:10:00] Mira: Focus block #deepwork\n"
            "[2026-03-31 11:12:01] Mira: Done"
        )

        records = parse_telegram_export(raw)

        self.assertEqual(2, len(records))
        self.assertEqual("telegram", records[0].source)
        self.assertEqual(["deepwork"], records[0].tags)
        self.assertIn("31.03.26", records[0].metadata["timestamp"])

    def test_local_notes_parser_uses_non_empty_lines(self) -> None:
        raw = "\n- Draft launch checklist #launch\n\n* Pair on review #team #launch\n"

        records = parse_local_notes(raw, note_id_prefix="daily")

        self.assertEqual(2, len(records))
        self.assertEqual("local_notes", records[0].source)
        self.assertEqual("daily:2", records[0].source_id)
        self.assertEqual(["launch"], records[0].tags)
        self.assertEqual(["team", "launch"], records[1].tags)


if __name__ == "__main__":
    unittest.main()
