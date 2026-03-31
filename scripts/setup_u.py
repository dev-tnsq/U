from __future__ import annotations

import argparse
import shutil
import socket
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from u_core.memory import SQLiteStore


@dataclass(frozen=True)
class SetupResult:
    data_dir: Path
    database_path: Path
    used_fallback_dir: bool
    ollama_available: bool


def default_primary_data_dir() -> Path:
    return Path.home() / "Library" / "Application Support" / "U"


def default_fallback_data_dir() -> Path:
    return Path.home() / "U" / "data"


def ensure_data_dirs(primary: Path | None = None, fallback: Path | None = None) -> tuple[Path, bool]:
    primary_dir = primary or default_primary_data_dir()
    fallback_dir = fallback or default_fallback_data_dir()
    try:
        primary_dir.mkdir(parents=True, exist_ok=True)
        for child in ("db", "runtime"):
            (primary_dir / child).mkdir(parents=True, exist_ok=True)
        return primary_dir, False
    except OSError:
        fallback_dir.mkdir(parents=True, exist_ok=True)
        for child in ("db", "runtime"):
            (fallback_dir / child).mkdir(parents=True, exist_ok=True)
        return fallback_dir, True


@contextmanager
def block_network_calls() -> object:
    original_connect = socket.socket.connect
    original_connect_ex = socket.socket.connect_ex
    original_create_connection = socket.create_connection

    def _blocked_connect(*args: object, **kwargs: object) -> None:
        raise RuntimeError("Network calls are disabled during local setup validation.")

    def _blocked_connect_ex(*args: object, **kwargs: object) -> int:
        raise RuntimeError("Network calls are disabled during local setup validation.")

    def _blocked_create_connection(*args: object, **kwargs: object) -> socket.socket:
        raise RuntimeError("Network calls are disabled during local setup validation.")

    socket.socket.connect = _blocked_connect
    socket.socket.connect_ex = _blocked_connect_ex
    socket.create_connection = _blocked_create_connection
    try:
        yield
    finally:
        socket.socket.connect = original_connect
        socket.socket.connect_ex = original_connect_ex
        socket.create_connection = original_create_connection


def initialize_sqlite(database_path: Path) -> None:
    with SQLiteStore(database_path) as store:
        store.initialize()


def check_local_model_runtime(binary_name: str = "ollama") -> bool:
    return shutil.which(binary_name) is not None


def run_setup(primary_data_dir: Path | None = None, fallback_data_dir: Path | None = None) -> SetupResult:
    with block_network_calls():
        data_dir, used_fallback = ensure_data_dirs(primary=primary_data_dir, fallback=fallback_data_dir)
        database_path = data_dir / "db" / "memory.sqlite3"
        initialize_sqlite(database_path)
        ollama_available = check_local_model_runtime()

    return SetupResult(
        data_dir=data_dir,
        database_path=database_path,
        used_fallback_dir=used_fallback,
        ollama_available=ollama_available,
    )


def format_next_steps(result: SetupResult) -> str:
    fallback_note = "yes" if result.used_fallback_dir else "no"
    ollama_note = "available" if result.ollama_available else "not found"
    return "\n".join(
        [
            "U local setup complete.",
            f"- Data directory: {result.data_dir}",
            f"- Database: {result.database_path}",
            f"- Fallback directory used: {fallback_note}",
            f"- Local model runtime (ollama): {ollama_note}",
            "",
            "Next steps:",
            "1. If ollama is not found, install it manually and ensure it is on PATH.",
            "2. Start your local model runtime (example: `ollama serve`).",
            "3. Continue with local usage flows from the project README.",
        ]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="First-run local setup for U.")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=None,
        help="Optional override for the primary data directory.",
    )
    parser.add_argument(
        "--fallback-dir",
        type=Path,
        default=None,
        help="Optional override for the fallback data directory.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = run_setup(primary_data_dir=args.data_dir, fallback_data_dir=args.fallback_dir)
    print(format_next_steps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())