import pytest

from agent.tool_router import RegisteredTool, ToolRouter
from models.engineering_contract import (
    CalculationRequest, CalculationResultPacket, Criterion, CriterionType,
    EngineeringMethodDecision, InputSource, WaterProperties,
)
from standards.criteria import validate_criteria
from standards.retrieval import build_criteria_packet, require_criterion
from calculations.pipe_sizing import size_pipe_candidates, select_first_acceptable, select_with_acceptance_criteria


def criterion(cid="v1", ctype=CriterionType.VELOCITY, parameter="max_velocity", value=1.5):
    return Criterion(
        criterion_id=cid, criterion_type=ctype, parameter=parameter, value=value,
        unit="m/s", application="transfer", applicability="ordinary building water",
        source_reference_id="ref-1", source_status="VERIFIED"
    )


def test_invalid_criterion_rejected():
    bad = criterion()
    bad = bad.model_copy(update={"source_reference_id": ""})
    assert validate_criteria([bad])


def test_rag_context_is_filtered_by_application_and_jurisdiction():
    c1 = criterion("transfer-v")
    c2 = criterion("booster-v").model_copy(update={"application": "booster"})
    got = build_criteria_packet([c1, c2], application="transfer")
    assert [x.criterion_id for x in got] == ["transfer-v"]


def test_multiple_matching_criteria_requires_resolution():
    with pytest.raises(LookupError):
        require_criterion([criterion("a"), criterion("b")], criterion_type="VELOCITY", parameter="max_velocity")


def test_request_carries_explicit_sources_and_method():
    req = CalculationRequest(
        request_id="r1", application="transfer", tool_name="pipe_loss",
        inputs={"flow_m3s": 0.005, "diameter_m": 0.05},
        input_sources={"flow_m3s": InputSource.CALCULATED},
        criterion_ids=["v1"], purpose="size transfer pipe",
        method_decision=EngineeringMethodDecision(
            application="transfer", hydraulic_method="Hazen-Williams",
            reason="criteria packet permits it", criterion_reference_ids=["v1"]
        ),
        water_properties=WaterProperties(
            temperature_c=20, density_kg_m3=998, dynamic_viscosity_pa_s=0.001002,
            source_reference_id="water-1", source_status="VERIFIED"
        )
    )
    assert req.water_properties.density_kg_m3 == 998
    assert req.method_decision.hydraulic_method == "Hazen-Williams"


def test_router_never_accepts_non_deterministic_tool():
    router = ToolRouter()
    with pytest.raises(ValueError):
        router.register(RegisteredTool("ai_number", lambda: 1, "not deterministic", deterministic=False))


def test_router_returns_deterministic_result():
    router = ToolRouter()
    router.register(RegisteredTool("double", lambda x: x * 2, "deterministic test"))
    req = CalculationRequest(request_id="r2", application="test", tool_name="double", inputs={"x": 4}, purpose="test")
    result = router.execute(req)
    assert isinstance(result, CalculationResultPacket)
    assert result.value == 8
    assert result.authoritative_numeric_source == "DETERMINISTIC_TOOL"


def test_pipe_selection_requires_hydraulic_acceptance_when_loss_is_used():
    candidates = size_pipe_candidates(
        0.005, "MS/carbon steel", velocity_min_mps=0.5, velocity_max_mps=2.0,
        hazen_williams_c=140, length_m=100
    )
    assert select_with_acceptance_criteria(candidates) is None


def test_pipe_selection_can_use_rag_head_loss_limit():
    candidates = size_pipe_candidates(
        0.005, "MS/carbon steel", velocity_min_mps=0.5, velocity_max_mps=2.0,
        hazen_williams_c=140, length_m=100, max_head_loss_m=10
    )
    selected = select_with_acceptance_criteria(candidates)
    assert selected is not None
    assert selected.hydraulic_status == "PASS"
