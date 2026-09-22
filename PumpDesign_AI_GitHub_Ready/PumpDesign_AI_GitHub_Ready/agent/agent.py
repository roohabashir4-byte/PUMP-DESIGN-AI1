"""Groq-backed PumpDesign AI agent with RAG and deterministic tool orchestration."""
from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable

from models.engineering_contract import Criterion
from standards.retrieval import build_criteria_packet
from agent.engineering_tools import build_engineering_router
from agent.prompts import SYSTEM_PROMPT, RAG_TOOL_DESCRIPTION


APPLICATIONS = {
    "transfer": "TRANSFER",
    "transfer_pump": "TRANSFER",
    "booster": "BOOSTER",
    "booster_pump": "BOOSTER",
    "submersible": "SUBMERSIBLE",
    "submersible_pump": "SUBMERSIBLE",
    "hot_water_recirc": "HOT_WATER_RECIRCULATION",
    "hot_water_recirculation": "HOT_WATER_RECIRCULATION",
}


@dataclass
class AgentState:
    rag_context: dict[str, Any] = field(default_factory=dict)
    messages: list[dict[str, Any]] = field(default_factory=list)
    last_tool_results: list[dict[str, Any]] = field(default_factory=list)


class PumpDesignAgent:
    """Orchestrates LLM reasoning, RAG retrieval and deterministic workflows.

    ``rag_retriever`` must return a list of Criterion objects or dictionaries
    representing the same fields. It is intentionally injected so the agent can
    later connect to FAISS/vector RAG without changing the orchestration layer.
    """

    def __init__(
        self,
        *,
        model: str | None = None,
        api_key: str | None = None,
        rag_retriever: Callable[..., list[Criterion | dict[str, Any]]] | None = None,
        max_tool_rounds: int = 8,
        client: Any | None = None,
    ):
        self.model = model or os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        self.rag_retriever = rag_retriever
        self.max_tool_rounds = max_tool_rounds
        self._state = AgentState()
        self._client = client
        self.router = build_engineering_router(lambda: self._state.rag_context)

    @property
    def state(self) -> AgentState:
        return self._state

    def _get_client(self):
        if self._client is not None:
            return self._client
        if not self.api_key:
            raise RuntimeError("GROQ_API_KEY is required to run the LLM agent.")
        try:
            from groq import Groq
        except ImportError as exc:
            raise RuntimeError("Install the 'groq' package before running the LLM agent.") from exc
        self._client = Groq(api_key=self.api_key)
        return self._client

    def _rag_context(self, application: str, service: str | None, jurisdiction: str | None, query: str | None = None, material: str | None = None) -> dict[str, Any]:
        if self.rag_retriever is None:
            raise RuntimeError("No RAG retriever is configured.")
        retrieval_query = query or application
        if material:
            retrieval_query = f"{retrieval_query} {material} Hazen Williams pipe material"
        raw = self.rag_retriever(application=application, service=service, jurisdiction=jurisdiction, query=retrieval_query)
        criteria: list[Criterion] = []
        for item in raw:
            criteria.append(item if isinstance(item, Criterion) else Criterion.model_validate(item))
        packet = build_criteria_packet(
            criteria,
            application=application,
            service=service,
            jurisdiction=jurisdiction,
        )
        velocity = [c for c in packet if c.criterion_type.value == "VELOCITY"]
        hw = [c for c in packet if c.criterion_type.value == "MATERIAL" and c.parameter.lower() in {"hazen_williams_c", "hazen_williams_c_value"}]
        # The existing deterministic workflows accept one velocity criterion
        # object and one Hazen-Williams C value. Do not silently choose between
        # conflicting records; make ambiguity visible to the agent.
        if material:
            mat = material.lower()
            aliases = [mat]
            if "steel" in mat or mat in {"ms", "carbon steel", "ms/carbon steel"}:
                aliases.extend(["steel", "steel pipe"])
            if "pvc" in mat:
                aliases.extend(["pvc", "plastic pipe"])
            if "hdpe" in mat or "pe" in mat:
                aliases.extend(["pe / polyethylene", "plastic pipe", "plastic"])
            if "copper" in mat:
                aliases.extend(["copper", "copper tubing"])
            hw = [c for c in hw if any(alias in c.applicability.lower() for alias in aliases)]
        if len(hw) > 1:
            primary = [c for c in hw if "PRIMARY" in c.source_status.upper()]
            new_pipe = [c for c in primary if "new" in c.applicability.lower()]
            if len(new_pipe) == 1:
                hw = new_pipe
            elif len(primary) == 1:
                hw = primary
            else:
                raise ValueError("Multiple Hazen-Williams C criteria matched; source precedence/pipe condition must be resolved first.")
        velocity_context: dict[str, float] = {}
        for c in velocity:
            key = c.parameter.lower()
            if key in {"min_velocity", "minimum_velocity", "velocity_min"} and c.value is not None:
                if "min_mps" in velocity_context and velocity_context["min_mps"] != c.value:
                    raise ValueError("Conflicting minimum velocity criteria matched.")
                velocity_context["min_mps"] = c.value
            elif key in {"max_velocity", "maximum_velocity", "velocity_max"} and c.value is not None:
                if "max_mps" in velocity_context and velocity_context["max_mps"] != c.value:
                    raise ValueError("Conflicting maximum velocity criteria matched.")
                velocity_context["max_mps"] = c.value
        self._state.rag_context = {
            "criteria": [c.model_dump(mode="json") for c in packet],
            "references": sorted({c.source_reference_id for c in packet}),
            "velocity_criteria": velocity_context or None,
            "hazen_williams_c": hw[0].value if hw else None,
        }
        return self._state.rag_context

    def _rag_tool(self, args: dict[str, Any]) -> dict[str, Any]:
        app_raw = str(args.get("application", "")).lower().strip()
        application = APPLICATIONS.get(app_raw, app_raw.upper())
        if application not in {"TRANSFER", "BOOSTER", "SUBMERSIBLE", "HOT_WATER_RECIRCULATION"}:
            raise ValueError(f"Unsupported pump application: {application}")
        return self._rag_context(application, args.get("service"), args.get("jurisdiction"), args.get("query"), args.get("material"))

    def _tool_schemas(self) -> list[dict[str, Any]]:
        schemas = [{
            "type": "function",
            "function": {
                "name": "get_engineering_criteria",
                "description": RAG_TOOL_DESCRIPTION,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "application": {"type": "string"},
                        "service": {"type": "string"},
                        "jurisdiction": {"type": "string"},
                        "query": {"type": "string"},
                        "material": {"type": "string"},
                    },
                    "required": ["application"],
                },
            }
        }]
        for name in self.router.available_tools():
            tool = self.router.get(name)
            schemas.append({
                "type": "function",
                "function": {
                    "name": name,
                    "description": tool.description,
                    "parameters": tool.input_schema or {"type": "object", "additionalProperties": True},
                },
            })
        return schemas

    def _execute_tool_call(self, name: str, args: dict[str, Any]) -> Any:
        if name == "get_engineering_criteria":
            return self._rag_tool(args)
        if name not in self.router.available_tools():
            raise LookupError(f"Unknown agent tool: {name}")
        # The LLM is not allowed to call a workflow before RAG context exists.
        if not self._state.rag_context:
            raise RuntimeError("Engineering criteria must be retrieved before running a design workflow.")
        # Workflows are deterministic; the router is the numerical authority.
        from models.engineering_contract import CalculationRequest
        req = CalculationRequest(
            request_id=str(uuid.uuid4()),
            application=name,
            tool_name=name,
            inputs=args,
            purpose="Agent-orchestrated pump design calculation",
        )
        result = self.router.execute(req)
        return result.model_dump(mode="json")

    def run(self, user_request: str, *, context: dict[str, Any] | None = None) -> str:
        """Run the agent tool loop and return the final engineering explanation."""
        client = self._get_client()
        self._state = AgentState()
        messages: list[dict[str, Any]] = [{"role": "system", "content": SYSTEM_PROMPT}]
        if context:
            messages.append({
                "role": "system",
                "content": "Structured project context supplied by the user/app:\n" + json.dumps(context, default=str),
            })
        messages.append({"role": "user", "content": user_request})
        self._state.messages = messages

        for _ in range(self.max_tool_rounds):
            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=800,
                tools=self._tool_schemas(),
                tool_choice="auto",
                temperature=0,
            )
            message = response.choices[0].message
            tool_calls = getattr(message, "tool_calls", None) or []
            if not tool_calls:
                final = message.content or "No final response was returned by the model."
                self._state.messages = messages + [{"role": "assistant", "content": final}]
                return final

            assistant_message: dict[str, Any] = {
                "role": "assistant",
                "content": message.content or "",
                "tool_calls": [],
            }
            for call in tool_calls:
                fn = call.function
                call_id = call.id
                try:
                    args = json.loads(fn.arguments or "{}")
                    result = self._execute_tool_call(fn.name, args)
                    if fn.name != "get_engineering_criteria":
                        self._state.last_tool_results.append({"tool": fn.name, "result": result})
                except Exception as exc:
                    result = {"status": "TOOL_ERROR", "message": str(exc)}
                assistant_message["tool_calls"].append({
                    "id": call_id,
                    "type": "function",
                    "function": {"name": fn.name, "arguments": fn.arguments},
                })
                messages.append(assistant_message)
                messages.append({
                    "role": "tool",
                    "tool_call_id": call_id,
                    "content": json.dumps(result, default=str),
                })
            self._state.messages = messages

        raise RuntimeError("Agent exceeded the maximum tool-call rounds without producing a final response.")
