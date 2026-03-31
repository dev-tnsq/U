from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from u_core.ingest import NormalizedRecord, ingest_records
from u_core.memory import SQLiteStore


class TestIngestService(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "memory.db"
        self.schema_path = ROOT / "src" / "u_core" / "memory" / "schema.sql"
        self.store = SQLiteStore(self.db_path, self.schema_path)
        self.store.initialize()

    def tearDown(self) -> None:
        self.store.close()
        self.tmp_dir.cleanup()

    def test_ingest_records_writes_events_with_source_metadata(self) -> None:
        records = [
            NormalizedRecord(
                source="whatsapp",
                source_id="w:1",
                content="Ship update",
                tags=["release"],
                metadata={"sender": "Alex", "timestamp": "3/31/26, 9:41 PM"},
            )
        ]

        events = ingest_records(self.store, records, event_type="ingest.whatsapp")

        self.assertEqual(1, len(events))
        self.assertEqual("ingest.whatsapp", events[0].event_type)
        self.assertEqual("Ship update", events[0].content)
        self.assertEqual("whatsapp", events[0].metadata["source"])
        self.assertEqual("w:1", events[0].metadata["source_id"])
        self.assertEqual(["release"], events[0].metadata["tags"])
        self.assertEqual("Alex", events[0].metadata["sender"])

        listed = self.store.list_events(limit=10, event_type="ingest.whatsapp")
        self.assertEqual(1, len(listed))
        self.assertEqual("Alex", listed[0].metadata["sender"])


if __name__ == "__main__":
    unittest.main()