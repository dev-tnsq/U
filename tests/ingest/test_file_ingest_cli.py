from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.ingest_data import (
    enforce_scope,
    parse_exclude_parts,
    parse_extensions,
    parse_app_roots,
    resolve_roots,
    safe_settings_snapshot,
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

    def test_parse_app_roots_defaults_and_expansion(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)

            parsed = parse_app_roots(raw="/Applications,~/Applications", home=home)

            self.assertEqual([Path("/Applications").resolve(), (home / "Applications").resolve()], parsed)

    def test_enforce_scope_rejects_and_allows_expected_scope(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "apps:read"):
            enforce_scope({"memory:write"}, "apps:read", "app inventory collection")

        enforce_scope({"memory:write", "apps:read"}, "apps:read", "app inventory collection")

    def test_safe_settings_snapshot_excludes_secret_like_keys(self) -> None:
        env = {
            "PATH": "/usr/bin",
            "HOME": "/tmp/home",
            "LANG": "en_US.UTF-8",
            "SHELL": "/bin/zsh",
            "API_TOKEN": "should-not-appear",
            "ACCESS_KEY": "should-not-appear",
            "TOP_SECRET": "should-not-appear",
            "TZ": "UTC",
        }

        snapshot = safe_settings_snapshot(env)

        self.assertEqual("/usr/bin", snapshot["PATH"])
        self.assertEqual("/tmp/home", snapshot["HOME"])
        self.assertEqual("en_US.UTF-8", snapshot["LANG"])
        self.assertEqual("/bin/zsh", snapshot["SHELL"])
        self.assertEqual("UTC", snapshot["TZ"])
        self.assertNotIn("API_TOKEN", snapshot)
        self.assertNotIn("ACCESS_KEY", snapshot)
        self.assertNotIn("TOP_SECRET", snapshot)

    def test_sample_text_truncates_at_limit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            file_path = Path(tmp) / "note.txt"
            file_path.write_text("a" * 5005, encoding="utf-8")

            sampled = sample_text(file_path, max_chars=4000)

            self.assertEqual(4000, len(sampled))
            self.assertEqual("a" * 4000, sampled)


if __name__ == "__main__":
    unittest.main()