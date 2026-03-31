from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from u_app.gradio_app import launch


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the local U Gradio MVP app.")
    parser.add_argument(
        "--db-path",
        type=Path,
        default=None,
        help="Optional path to SQLite memory database.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    launch(db_path=args.db_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
