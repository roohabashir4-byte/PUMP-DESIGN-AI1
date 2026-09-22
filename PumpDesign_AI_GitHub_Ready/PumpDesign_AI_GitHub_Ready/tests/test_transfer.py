
from engineering.transfer import run_transfer_design

def base():
    return {
        "demand_method": "TOTAL",
        "total_design_demand": {"value": 100000, "unit": "gpd"},
        "oht_capacity": {"value": 25000, "unit": "gal"},
        "ugt_design_water_level": {"value": -22, "unit": "ft"},
        "oht_design_water_level": {"value": 160, "unit": "ft"},
        "required_transfer_time": {"value": 90, "unit": "min"},
        "suction_pipe_length": {"value": 20, "unit": "ft"},
        "delivery_pipe_length": {"value": 200, "unit": "ft"},
        "pipe_material": "MS",
    }

def test_transfer_flow_and_static_head():
    result = run_transfer_design(base())
    names = {c["name"]: c for c in result["calculations"]}
    assert names["Transfer design flow"]["status"] == "CALCULATED"
    assert abs(names["Transfer design flow"]["value"] - 25000/90) < 1e-9
    assert abs(names["Static head"]["value"] - 182*0.3048) < 1e-9

def test_transfer_does_not_select_pipe_without_velocity_criterion():
    result = run_transfer_design(base())
    assert result["pipe_sizing"]["suction"]["selection_status"] == "NOT_SELECTED"
    assert result["pipe_sizing"]["delivery"]["selection_status"] == "NOT_SELECTED"
    assert any(v["name"] == "TDH completeness" for v in result["validation"])

def test_transfer_uses_supplied_rag_criteria_for_selection():
    rag = {
        "velocity_criteria": {"min_mps": None, "max_mps": 1.5},
        "hazen_williams_c": 140,
        "references": [{"title": "test criterion"}],
    }
    result = run_transfer_design(base(), rag_context=rag)
    assert result["pipe_sizing"]["delivery"]["selection_status"] == "SELECTED"
    names = {c["name"]: c for c in result["calculations"]}
    assert names["Total Dynamic Head"]["status"] == "CALCULATED"
    assert names["Hydraulic power"]["status"] == "CALCULATED"
