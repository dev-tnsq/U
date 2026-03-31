"""Local tool registry for planner runtime tool actions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Literal

ToolRisk = Literal["read_only", "reversible_write", "irreversible_write"]


@dataclass(frozen=True)
class RegisteredTool:
    """Tool entry with risk metadata and callable handler."""

    name: str
    risk: ToolRisk
    handler: Callable[[dict[str, Any]], str]
    description: str


class ToolRegistry:
    """In-memory registry for named planner tools."""

    def __init__(self) -> None:
        self._tools: dict[str, RegisteredTool] = {}

    def register(self, tool: RegisteredTool) -> None:
        """Register a tool by name, rejecting duplicates."""
        if tool.name in self._tools:
            raise ValueError(f"tool already registered: {tool.name}")
        self._tools[tool.name] = tool

    def get(self, name: str) -> RegisteredTool:
        """Return a registered tool or raise a clear error."""
        try:
            return self._tools[name]
        except KeyError as err:
            raise KeyError(f"unknown tool: {name}") from err

    def list_tools(self) -> list[RegisteredTool]:
        """Return registered tools in deterministic order."""
        return [self._tools[name] for name in sorted(self._tools)]

    def execute(self, name: str, payload: dict[str, Any]) -> str:
        """Execute a registered tool by name with payload."""
        tool = self.get(name)
        return tool.handler(payload)