from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from u_core.memory import ProfileStore, SQLiteStore


class TestProfileStore(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "memory.db"
        self.schema_path = ROOT / "src" / "u_core" / "memory" / "schema.sql"
        self.store = SQLiteStore(self.db_path, self.schema_path)
        self.store.initialize()
        self.profile_store = ProfileStore(self.store)

    def tearDown(self) -> None:
        self.store.close()
        self.tmp_dir.cleanup()

    def test_profile_update_increments_version(self) -> None:
        p1 = self.profile_store.update_profile({"name": "U", "tone": "concise"})
        p2 = self.profile_store.update_profile({"name": "U", "tone": "detailed"})
        loaded = self.profile_store.load_profile()

        self.assertEqual(1, p1.version)
        self.assertEqual(2, p2.version)
        self.assertIsNotNone(loaded)
        self.assertEqual("detailed", loaded.data["tone"])


if __name__ == "__main__":
    unittest.main()
