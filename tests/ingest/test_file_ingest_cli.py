from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.ingest_data import (
    parse_exclude_parts,
    parse_extensions,
    resolve_roots,
    sample_text,
    should_exclude_path,
)


class TestFileIngestCLIHelpers(unittest.TestCase):
    def test_resolve_roots_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            expected_home = home.resolve()

            roots = resolve_roots(roots_raw=None, include_home=False, home=home)

            self.assertEqual(
                [
                    expected_home / "Desktop",
                    expected_home / "Documents",
                    expected_home / "Downloads",
                    expected_home / "code",
                ],
                roots,
            )

    def test_resolve_roots_include_home_overrides_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)

            roots = resolve_roots(roots_raw=None, include_home=True, home=home)

            self.assertEqual([home.resolve()], roots)

    def test_parse_extensions_and_exclude_filtering(self) -> None:
        extensions = parse_extensions(".TXT, md, json ,")
        excludes = parse_exclude_parts(".git,node_modules,__pycache__")

        self.assertEqual({"txt", "md", "json"}, extensions)
        self.assertTrue(should_exclude_path(Path("/tmp/project/.git/config"), excludes))
        self.assertTrue(should_exclude_path(Path("/tmp/project/node_modules/pkg/index.js"), excludes))
        self.assertFalse(should_exclude_path(Path("/tmp/project/src/main.py"), excludes))

    def test_sample_text_truncates_at_limit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            file_path = Path(tmp) / "note.txt"
            file_path.write_text("a" * 5005, encoding="utf-8")

            sampled = sample_text(file_path, max_chars=4000)

            self.assertEqual(4000, len(sampled))
            self.assertEqual("a" * 4000, sampled)


if __name__ == "__main__":
    unittest.main()