"""Deterministic, local-only macOS tool adapters for planner runtime."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .tools import RegisteredTool, ToolRegistry


def _clamp_int(raw: object, *, default: int, minimum: int, maximum: int) -> int:
    if isinstance(raw, bool):
        return default
    if isinstance(raw, int):
        value = raw
    elif isinstance(raw, str):
        try:
            value = int(raw.strip())
        except ValueError:
            return default
    else:
        return default
    return max(minimum, min(maximum, value))


def _is_hidden(path: Path) -> bool:
    return any(part.startswith(".") for part in path.parts)


def handle_file_search(payload: dict[str, Any]) -> str:
    """Search plain-text content under a root path using capped deterministic traversal."""
    query = str(payload.get("query", "")).strip()
    root_path = Path(str(payload.get("root_path", "."))).expanduser().resolve()
    max_files = _clamp_int(payload.get("max_files"), default=100, minimum=1, maximum=500)
    max_matches = _clamp_int(payload.get("max_matches"), default=25, minimum=1, maximum=250)
    max_file_bytes = _clamp_int(
        payload.get("max_file_bytes"),
        default=1_000_000,
        minimum=256,
        maximum=2_000_000,
    )
    include_hidden = bool(payload.get("include_hidden", False))

    if not query:
        result = {
            "tool": "file_search",
            "status": "invalid_payload",
            "reason": "query must be a non-empty string",
            "query": query,
            "root_path": str(root_path),
            "files_scanned": 0,
            "matches": [],
            "truncated": False,
        }
        return json.dumps(result, sort_keys=True)

    if not root_path.exists() or not root_path.is_dir():
        result = {
            "tool": "file_search",
            "status": "missing_root",
            "reason": "root_path does not exist or is not a directory",
            "query": query,
            "root_path": str(root_path),
            "files_scanned": 0,
            "matches": [],
            "truncated": False,
        }
        return json.dumps(result, sort_keys=True)

    matches: list[dict[str, Any]] = []
    files_scanned = 0
    query_folded = query.casefold()

    for path in sorted(root_path.rglob("*"), key=lambda item: str(item.relative_to(root_path))):
        if files_scanned >= max_files or len(matches) >= max_matches:
            break
        if not path.is_file():
            continue

        rel_path = path.relative_to(root_path)
        if not include_hidden and _is_hidden(rel_path):
            continue

        files_scanned += 1
        try:
            raw = path.read_bytes()[:max_file_bytes]
        except OSError:
            continue

        text = raw.decode("utf-8", errors="ignore")
        for line_number, line in enumerate(text.splitlines(), start=1):
            if query_folded not in line.casefold():
                continue
            matches.append(
                {
                    "path": rel_path.as_posix(),
                    "line": line_number,
                    "snippet": line.strip(),
                }
            )
            if len(matches) >= max_matches:
                break

    result = {
        "tool": "file_search",
        "status": "ok",
        "query": query,
        "root_path": str(root_path),
        "files_scanned": files_scanned,
        "matches": matches,
        "truncated": files_scanned >= max_files or len(matches) >= max_matches,
    }
    return json.dumps(result, sort_keys=True)


def handle_app_open_preview(payload: dict[str, Any]) -> str:
    """Return a structured preview for app-open action without executing anything."""
    app_name = str(payload.get("app_name", "")).strip()
    if not app_name:
        app_name = "Preview"

    args_raw = payload.get("args")
    args: list[str]
    if isinstance(args_raw, list):
        args = [str(item) for item in args_raw]
    else:
        args = []

    result = {
        "tool": "app_open_preview",
        "status": "preview_only",
        "will_execute": False,
        "action": {
            "kind": "open_application",
            "app_name": app_name,
            "args": args,
        },
    }
    return json.dumps(result, sort_keys=True)


def handle_calendar_draft_event(payload: dict[str, Any]) -> str:
    """Build a deterministic calendar event draft payload with no external side effects."""
    title = str(payload.get("title", "")).strip() or "Untitled Event"
    starts_at = str(payload.get("starts_at", "")).strip()
    ends_at = str(payload.get("ends_at", "")).strip()
    location = str(payload.get("location", "")).strip()
    notes = str(payload.get("notes", "")).strip()

    draft_event = {
        "title": title,
        "starts_at": starts_at,
        "ends_at": ends_at,
        "location": location,
        "notes": notes,
    }
    digest_input = json.dumps(draft_event, sort_keys=True)
    draft_id = hashlib.sha256(digest_input.encode("utf-8")).hexdigest()[:16]

    result = {
        "tool": "calendar_draft_event",
        "status": "draft",
        "draft_id": draft_id,
        "event": draft_event,
    }
    return json.dumps(result, sort_keys=True)


def build_default_macos_tool_registry() -> ToolRegistry:
    """Create default local-safe macOS registry for planner runtime."""
    registry = ToolRegistry()
    registry.register(
        RegisteredTool(
            name="file_search",
            risk="read_only",
            handler=handle_file_search,
            description="Search for text in local files under a bounded root path.",
        )
    )
    registry.register(
        RegisteredTool(
            name="app_open_preview",
            risk="reversible_write",
            handler=handle_app_open_preview,
            description="Create a preview-only app open action without executing it.",
        )
    )
    registry.register(
        RegisteredTool(
            name="calendar_draft_event",
            risk="reversible_write",
            handler=handle_calendar_draft_event,
            description="Create a local draft payload for a calendar event.",
        )
    )
    return registry
