"""Deterministic engineering tool registry and execution boundary."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from models.engineering_contract import CalculationRequest, CalculationResultPacket


@dataclass(frozen=True)
class RegisteredTool:
    name: str
    function: Callable[..., Any]
    description: str
    deterministic: bool = True
    input_schema: dict[str, Any] | None = None


class ToolRouter:
    """Only deterministic engineering functions may cross this boundary."""

    def __init__(self):
        self._tools: dict[str, RegisteredTool] = {}

    def register(self, tool: RegisteredTool) -> None:
        if not tool.deterministic:
            raise ValueError("Only deterministic engineering tools may be registered.")
        if tool.name in self._tools:
            raise ValueError(f"Tool already registered: {tool.name}")
        self._tools[tool.name] = tool

    def available_tools(self) -> list[str]:
        return sorted(self._tools)

    def get(self, name: str) -> RegisteredTool:
        tool = self._tools.get(name)
        if tool is None:
            raise LookupError(f"Unknown calculation tool: {name}")
        return tool

    def execute(self, request: CalculationRequest) -> CalculationResultPacket:
        tool = self.get(request.tool_name)
        if not request.inputs:
            raise ValueError("Calculation request must contain inputs.")
        raw = tool.function(**request.inputs)
        if isinstance(raw, CalculationResultPacket):
            return raw
        return CalculationResultPacket(
            request_id=request.request_id,
            tool_name=request.tool_name,
            status="CALCULATED",
            value=raw,
            criterion_ids=request.criterion_ids,
        )
