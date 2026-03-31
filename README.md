# U

## Memory Core (Initial Scaffold)

The memory core is designed for local-first, offline operation on macOS-class developer machines.

- SQLite-backed structured memory (`events`, `reflections`, `profiles`, `graph_edges`)
- Schema bootstrap and baseline migration tracking from `src/u_core/memory/schema.sql`
- In-memory vector store fallback for lightweight semantic retrieval experiments

### Quick Usage

```python
from pathlib import Path

from u_core.memory import GraphStore, ProfileStore, SQLiteStore

store = SQLiteStore(Path("./data/memory.db"))
store.initialize()

event = store.create_event("action", "ran local pipeline", {"status": "ok"})
profile_store = ProfileStore(store)
profile = profile_store.update_profile({"name": "U", "prefs": {"verbosity": "low"}})

graph_store = GraphStore(store)
graph_store.upsert_edge("u", "pipeline", "uses", weight=0.9)

store.close()
```

## First-run setup

Run the local setup script to bootstrap data directories and initialize SQLite:

```bash
python scripts/setup_u.py
```

The script creates local data directories under `~/Library/Application Support/U` (or `~/U/data` fallback), initializes the database schema, checks for `ollama` on your PATH, and prints actionable next steps.

## Run UI

Launch the local Gradio MVP to preview side-by-side Supportive U and Honest U outputs plus a planner preview panel.

```bash
pip install gradio
python scripts/run_ui.py
```

Optional: provide a custom SQLite path.

```bash
python scripts/run_ui.py --db-path /path/to/memory.sqlite3
```

## Quality Check

Run the local quality gate before opening or updating a PR:

```bash
python scripts/check_quality.py
```

This runs compile sanity for `src`, `tests`, and `scripts`, then executes `pytest tests`.

## Release Flow

v0.1.0 release path:

1. Create `release/v0.1.0` from `develop`.
2. Run local and CI quality gates on the release branch.
3. Finalize changelog and release notes.
4. Merge `release/v0.1.0` into `main` and tag `v0.1.0`.
5. Back-merge `main` into `develop`.

See `docs/release-checklist.md` for the concise release checklist.
