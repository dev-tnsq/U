# Repository Guidelines

## Project Structure & Module Organization
The codebase follows a local-first, offline-ready architecture for developer machines, split into core logic and application layers:

- **`src/u_core/`**: Core engine modules including memory (SQLite-backed), agent runtime, ingestion parsers (Telegram/WhatsApp/Notes), reflection engine, and the "Twin" reasoning system.
- **`src/u_core/agent/`**: Planner schemas/runtime plus local-safe macOS tool adapters and default tool registry wiring.
- **`src/u_app/`**: Application interface logic, currently featuring a Gradio-based dual-response MVP.
- **`scripts/`**: Essential bootstrap and execution utilities.
- **`tests/`**: Organized by module (e.g., `tests/memory/`, `tests/twin/`), containing integration and e2e tests.

Modules often use `sys.path.insert(0, str(SRC))` for local development and test execution.

## Build, Test, and Development Commands
The project relies on a standard Python environment.

- **Initial Setup**: `python scripts/setup_u.py` (Bootstraps data directories and initializes SQLite).
- **Launch UI**: `python scripts/run_ui.py` (Starts the Gradio interface).
- **Run All Tests**: `pytest tests`
- **Run Specific Test**: `pytest tests/e2e/test_core_flow.py`

## Coding Style & Naming Conventions
- **Language**: Python 3.11+
- **Imports**: Prefers `from __future__ import annotations`.
- **Typing**: Uses type hints throughout for clarity and consistency.
- **Naming**: Standard Pythonic snake_case for functions/variables and PascalCase for classes.

## Testing Guidelines
- **Framework**: `pytest` is used as the test runner in CI, but tests are often implemented using the `unittest.TestCase` pattern.
- **Database**: Tests typically use `tempfile` to create isolated SQLite instances for stateful verification.

## Commit & Pull Request Guidelines
Commit messages follow a prefix-based convention:
- **`feat(...)`**: New features
- **`test(...)`**: Testing updates
- **`docs(...)`**: Documentation changes
- **`ci(...)`**: CI/CD configuration
- **`fix(...)`**: Bug fixes

Example: `feat(twin): add local inference runtime abstraction`
