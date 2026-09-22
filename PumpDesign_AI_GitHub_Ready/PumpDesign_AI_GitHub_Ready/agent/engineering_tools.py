"""Registration of the four deterministic PumpDesign AI workflows."""
from __future__ import annotations

from typing import Any

from engineering.booster import run_booster_design
from engineering.hot_water_recirc import run_hot_water_recirc_design
from engineering.submersible import run_submersible_design
from engineering.transfer import run_transfer_design
from agent.tool_router import RegisteredTool, ToolRouter


def build_engineering_router(rag_context_provider) -> ToolRouter:
    """Build a router whose workflow wrappers receive the agent's current RAG context."""
    router = ToolRouter()

    def run_transfer(**data: Any) -> dict:
        return run_transfer_design(data, rag_context=rag_context_provider())

    def run_booster(**data: Any) -> dict:
        return run_booster_design(data, rag_context=rag_context_provider())

    def run_submersible(**data: Any) -> dict:
        return run_submersible_design(data, rag_context=rag_context_provider())

    def run_hot_water_recirc(**data: Any) -> dict:
        return run_hot_water_recirc_design(data, rag_context=rag_context_provider())

    common = {
        "type": "object",
        "additionalProperties": True,
    }
    router.register(RegisteredTool(
        "run_transfer_design", run_transfer,
        "Run the deterministic UGT-to-OHT transfer pump design workflow. Supply only project/design inputs already known or derived by the agent.", common,
    ))
    router.register(RegisteredTool(
        "run_booster_design", run_booster,
        "Run the deterministic booster pump design workflow for the selected pressure zone.", common,
    ))
    router.register(RegisteredTool(
        "run_submersible_design", run_submersible,
        "Run the deterministic submersible pump design workflow.", common,
    ))
    router.register(RegisteredTool(
        "run_hot_water_recirc_design", run_hot_water_recirc,
        "Run the deterministic domestic hot-water recirculation pump workflow.", common,
    ))
    return router
