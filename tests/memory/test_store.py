from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from u_core.memory import GraphStore, SQLiteStore


class TestSQLiteStore(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "memory.db"
        self.schema_path = ROOT / "src" / "u_core" / "memory" / "schema.sql"
        self.store = SQLiteStore(self.db_path, self.schema_path)
        self.store.initialize()

    def tearDown(self) -> None:
        self.store.close()
        self.tmp_dir.cleanup()

    def test_event_crud(self) -> None:
        created = self.store.create_event("action", "opened file", {"path": "README.md"})
        self.assertIsNotNone(created.id)

        loaded = self.store.get_event(created.id or -1)
        self.assertIsNotNone(loaded)
        self.assertEqual("action", loaded.event_type)

        updated = self.store.update_event(created.id or -1, content="opened file + edited")
        self.assertIsNotNone(updated)
        self.assertEqual("opened file + edited", updated.content)

        deleted = self.store.delete_event(created.id or -1)
        self.assertTrue(deleted)

    def test_reflection_crud(self) -> None:
        created = self.store.create_reflection("summary", "daily recap", {"tokens": 42})
        self.assertIsNotNone(created.id)

        loaded = self.store.get_reflection(created.id or -1)
        self.assertIsNotNone(loaded)
        self.assertEqual("summary", loaded.kind)

        updated = self.store.update_reflection(created.id or -1, metadata={"tokens": 55})
        self.assertIsNotNone(updated)
        self.assertEqual(55, updated.metadata["tokens"])

        deleted = self.store.delete_reflection(created.id or -1)
        self.assertTrue(deleted)

    def test_graph_upsert_and_list(self) -> None:
        graph_store = GraphStore(self.store)
        graph_store.upsert_edge("u", "calendar", "uses", weight=0.8)
        graph_store.upsert_edge("u", "calendar", "uses", weight=0.95)

        edges = graph_store.list_edges(source="u", relation="uses")
        self.assertEqual(1, len(edges))
        self.assertEqual("calendar", edges[0].target)
        self.assertEqual(0.95, edges[0].weight)


if __name__ == "__main__":
    unittest.main()
