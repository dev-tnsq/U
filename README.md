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
