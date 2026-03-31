from __future__ import annotations

import importlib.util
import sqlite3
import socket
import sys
from pathlib import Path


def _load_setup_module():
    root = Path(__file__).resolve().parents[2]
    module_path = root / "scripts" / "setup_u.py"
    spec = importlib.util.spec_from_file_location("setup_u", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["setup_u"] = module
    spec.loader.exec_module(module)
    return module


def test_ensure_data_dirs_uses_primary_path(tmp_path: Path) -> None:
    setup_u = _load_setup_module()
    primary = tmp_path / "Library" / "Application Support" / "U"
    fallback = tmp_path / "U" / "data"

    data_dir, used_fallback = setup_u.ensure_data_dirs(primary=primary, fallback=fallback)

    assert data_dir == primary
    assert used_fallback is False
    assert (primary / "db").exists()
    assert (primary / "runtime").exists()


def test_ensure_data_dirs_falls_back_when_primary_fails(tmp_path: Path) -> None:
    setup_u = _load_setup_module()
    blocking_file = tmp_path / "Library"
    blocking_file.write_text("not-a-directory", encoding="utf-8")
    primary = blocking_file / "Application Support" / "U"
    fallback = tmp_path / "U" / "data"

    data_dir, used_fallback = setup_u.ensure_data_dirs(primary=primary, fallback=fallback)

    assert data_dir == fallback
    assert used_fallback is True
    assert (fallback / "db").exists()
    assert (fallback / "runtime").exists()


def test_initialize_sqlite_bootstraps_schema(tmp_path: Path) -> None:
    setup_u = _load_setup_module()
    database_path = tmp_path / "memory.sqlite3"

    setup_u.initialize_sqlite(database_path)

    conn = sqlite3.connect(database_path)
    try:
        tables = {
            row[0]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        }
        assert "schema_migrations" in tables
        assert "events" in tables
        assert "reflections" in tables
        version = conn.execute("SELECT version FROM schema_migrations").fetchone()
        assert version is not None
        assert version[0] == 1
    finally:
        conn.close()


def test_block_network_calls_blocks_then_restores() -> None:
    setup_u = _load_setup_module()

    with setup_u.block_network_calls():
        try:
            socket.create_connection(("localhost", 9), timeout=0.01)
            assert False, "expected network call to be blocked"
        except RuntimeError as exc:
            assert "disabled" in str(exc)

    try:
        socket.create_connection(("localhost", 9), timeout=0.01)
        assert False, "expected connection failure on closed local port"
    except OSError:
        pass


def test_check_local_model_runtime_uses_which(monkeypatch) -> None:
    setup_u = _load_setup_module()

    monkeypatch.setattr(setup_u.shutil, "which", lambda _: "/usr/local/bin/ollama")
    assert setup_u.check_local_model_runtime() is True

    monkeypatch.setattr(setup_u.shutil, "which", lambda _: None)
    assert setup_u.check_local_model_runtime() is False


def test_run_setup_creates_db_and_reports_next_steps(tmp_path: Path, monkeypatch) -> None:
    setup_u = _load_setup_module()
    primary = tmp_path / "Library" / "Application Support" / "U"
    fallback = tmp_path / "U" / "data"
    monkeypatch.setattr(setup_u, "check_local_model_runtime", lambda: False)

    result = setup_u.run_setup(primary_data_dir=primary, fallback_data_dir=fallback)
    message = setup_u.format_next_steps(result)

    assert result.data_dir == primary
    assert result.database_path.exists()
    assert "U local setup complete." in message
    assert "Next steps:" in message
    assert "not found" in message