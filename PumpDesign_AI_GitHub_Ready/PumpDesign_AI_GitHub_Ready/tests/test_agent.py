import json
from types import SimpleNamespace

import pytest

from agent.agent import PumpDesignAgent
from models.engineering_contract import Criterion, CriterionType


class FakeCompletions:
    def __init__(self):
        self.calls = 0

    def create(self, **kwargs):
        self.calls += 1
        if self.calls == 1:
            tool_call = SimpleNamespace(
                id="call-1",
                function=SimpleNamespace(
                    name="get_engineering_criteria",
                    arguments=json.dumps({"application": "transfer", "jurisdiction": "Pakistan"}),
                ),
            )
            message = SimpleNamespace(content=None, tool_calls=[tool_call])
        elif self.calls == 2:
            tool_call = SimpleNamespace(
                id="call-2",
                function=SimpleNamespace(
                    name="run_transfer_design",
                    arguments=json.dumps({
                        "oht_capacity": {"value": 25000, "unit": "US gal"},
                        "required_transfer_time": {"value": 90, "unit": "min"},
                        "ugt_design_water_level": {"value": -22, "unit": "ft"},
                        "oht_design_water_level": {"value": 160, "unit": "ft"},
                        "suction_pipe_length": {"value": 20, "unit": "ft"},
                        "delivery_pipe_length": {"value": 200, "unit": "ft"},
                        "pipe_material": "MS/carbon steel",
                    }),
                ),
            )
            message = SimpleNamespace(content=None, tool_calls=[tool_call])
        else:
            message = SimpleNamespace(content="Deterministic design workflow completed; review the returned warnings before issue.", tool_calls=[])
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


class FakeClient:
    def __init__(self):
        self.chat = SimpleNamespace(completions=FakeCompletions())


def retriever(**kwargs):
    return [
        Criterion(
            criterion_id="v-transfer",
            criterion_type=CriterionType.VELOCITY,
            parameter="max_velocity",
            value=3.0,
            unit="m/s",
            application="TRANSFER",
            applicability="test",
            source_reference_id="ref-1",
            source_status="VERIFIED",
        ),
        Criterion(
            criterion_id="c-steel",
            criterion_type=CriterionType.MATERIAL,
            parameter="hazen_williams_c",
            value=140,
            unit="-",
            application="TRANSFER",
            applicability="test",
            source_reference_id="ref-2",
            source_status="VERIFIED",
        ),
    ]


def test_agent_requires_rag_before_workflow():
    agent = PumpDesignAgent(client=FakeClient(), rag_retriever=retriever)
    assert agent.router.available_tools() == [
        "run_booster_design", "run_hot_water_recirc_design", "run_submersible_design", "run_transfer_design"
    ]


def test_agent_orchestrates_rag_then_deterministic_workflow():
    agent = PumpDesignAgent(client=FakeClient(), rag_retriever=retriever)
    answer = agent.run("Design the transfer pump for the supplied project.")
    assert "completed" in answer.lower()
    assert agent.state.rag_context["references"] == ["ref-1", "ref-2"]
    assert any(m.get("role") == "tool" for m in agent.state.messages)
