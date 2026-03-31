from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from u_core.agent.policy import ensure_policy_allows_runtime, load_policy
from u_core.memory import SQLiteStore

DEFAULT_EXCLUDE_PARTS = ".git,.venv,node_modules,__pycache__,.pytest_cache,Library"
DEFAULT_EXTENSIONS = "txt,md,json,csv,log,py,yaml,yml,toml"
METADATA_ONLY_MARKER = "[metadata-only]"
TEXT_SAMPLE_MAX_CHARS = 4000


def _default_db_path() -> Path:
    primary = Path.home() / "Library" / "Application Support" / "U" / "db" / "memory.sqlite3"
    fallback = Path.home() / "U" / "data" / "db" / "memory.sqlite3"

    try:
        primary.parent.mkdir(parents=True, exist_ok=True)
        return primary
    except OSError:
        fallback.parent.mkdir(parents=True, exist_ok=True)
        return fallback


def _default_roots(home: Path | None = None) -> list[Path]:
    base = home or Path.home()
    return [
        base / "Desktop",
        base / "Documents",
        base / "Downloads",
        base / "code",
    ]


def resolve_roots(roots_raw: str | None, include_home: bool, home: Path | None = None) -> list[Path]:
    base = home or Path.home()
    if include_home:
        return [base.resolve()]

    if roots_raw:
        roots = [Path(item.strip()).expanduser() for item in roots_raw.split(",") if item.strip()]
    else:
        roots = _default_roots(base)

    resolved: list[Path] = []
    seen: set[str] = set()
    for root in roots:
        absolute = root.resolve()
        key = str(absolute)
        if key in seen:
            continue
        seen.add(key)
        resolved.append(absolute)
    return resolved


def parse_extensions(raw: str | None) -> set[str]:
    target = raw if raw is not None else DEFAULT_EXTENSIONS
    result: set[str] = set()
    for item in target.split(","):
        value = item.strip().lower()
        if not value:
            continue
        result.add(value.lstrip("."))
    return result


def parse_exclude_parts(raw: str | None) -> set[str]:
    target = raw if raw is not None else DEFAULT_EXCLUDE_PARTS
    return {item.strip() for item in target.split(",") if item.strip()}


def should_exclude_path(path: Path, excluded_parts: set[str]) -> bool:
    return any(part in excluded_parts for part in path.parts)


def sample_text(path: Path, max_chars: int = TEXT_SAMPLE_MAX_CHARS) -> str:
    content = path.read_text(encoding="utf-8", errors="replace")
    return content[:max_chars]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest local files into U memory events.")
    parser.add_argument(
        "--roots",
        default=None,
        help="Comma-separated root paths to scan.",
    )
    parser.add_argument(
        "--include-home",
        action="store_true",
        help="Scan the entire home directory as a single root.",
    )
    parser.add_argument(
        "--max-files",
        type=int,
        default=6000,
        help="Maximum number of files to scan.",
    )
    parser.add_argument(
        "--max-bytes",
        type=int,
        default=200000,
        help="Maximum file size in bytes for text sampling.",
    )
    parser.add_argument(
        "--exclude-parts",
        default=DEFAULT_EXCLUDE_PARTS,
        help="Comma-separated path parts to exclude.",
    )
    parser.add_argument(
        "--extensions",
        default=DEFAULT_EXTENSIONS,
        help="Comma-separated file extensions allowed for text sampling.",
    )
    return parser.parse_args()


def _iter_files(roots: list[Path], excluded_parts: set[str]):
    for root in roots:
        if not root.exists() or not root.is_dir():
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            current_dir = Path(dirpath)
            dirnames[:] = [
                name
                for name in dirnames
                if not should_exclude_path(current_dir / name, excluded_parts)
            ]
            for filename in filenames:
                candidate = current_dir / filename
                if should_exclude_path(candidate, excluded_parts):
                    continue
                yield root, candidate


def _enforce_consent_and_scope() -> None:
    policy = load_policy()
    ensure_policy_allows_runtime(policy)
    if "memory:write" not in set(policy.allowed_scopes):
        raise RuntimeError("Policy violation: memory:write scope is required for local ingestion.")


def main() -> int:
    args = parse_args()
    if args.max_files <= 0:
        raise SystemExit("--max-files must be a positive integer")
    if args.max_bytes <= 0:
        raise SystemExit("--max-bytes must be a positive integer")

    _enforce_consent_and_scope()

    roots = resolve_roots(args.roots, args.include_home)
    extensions = parse_extensions(args.extensions)
    excluded_parts = parse_exclude_parts(args.exclude_parts)
    db_path = _default_db_path()

    scanned = 0
    ingested = 0
    errors = 0

    with SQLiteStore(db_path) as store:
        store.initialize()
        for root, file_path in _iter_files(roots, excluded_parts):
            if scanned >= args.max_files:
                break

            scanned += 1
            try:
                stat = file_path.stat()
                ext = file_path.suffix.lower().lstrip(".")
                is_text_sampled = ext in extensions and stat.st_size <= args.max_bytes
                if is_text_sampled:
                    content = sample_text(file_path)
                else:
                    content = METADATA_ONLY_MARKER
            except OSError:
                errors += 1
                continue

            metadata = {
                "path": str(file_path),
                "root": str(root),
                "size": int(stat.st_size),
                "mtime": int(stat.st_mtime),
                "ext": ext,
                "is_text_sampled": is_text_sampled,
            }
            store.create_event("ingest.local_file", content, metadata)
            ingested += 1

    print(f"DB_PATH={db_path}")
    print(f"ROOTS={','.join(str(root) for root in roots)}")
    print(f"SCANNED={scanned}")
    print(f"INGESTED={ingested}")
    print(f"ERRORS={errors}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())