
from engineering.booster import run_booster_design

def base():
    return {
        "demand_method": "TOTAL",
        "total_design_demand": {"value": 300, "unit": "gpm"},
        "oht_design_water_level": {"value": 80, "unit": "ft"},
        "available_inlet_pressure": {"value": 10, "unit": "psi"},
        "lowest_elevation_served": {"value": 90, "unit": "ft"},
        "highest_elevation_served": {"value": 190, "unit": "ft"},
        "required_residual_pressure": {"value": 20, "unit": "psi"},
        "critical_route_length": {"value": 250, "unit": "ft"},
        "pipe_material": "MS/carbon steel",
    }

def test_booster_missing_flow_does_not_use_daily_demand():
    d = base()
    d["total_design_demand"] = {"value": 100000, "unit": "gpd"}
    r = run_booster_design(d)
    assert r["status"] == "MISSING_INPUT"
    assert r["calculations"][0]["status"] == "MISSING_INPUT"

def test_booster_with_project_flow_and_rag_criteria():
    r = run_booster_design(
        base(),
        rag_context={
            "velocity_criteria": {"min_mps": None, "max_mps": 1.5},
            "hazen_williams_c": 140,
            "references": [{"title": "test criterion"}],
        },
    )
    c = {x["name"]: x for x in r["calculations"]}
    assert c["Booster design flow"]["status"] == "CALCULATED"
    assert c["Elevation head"]["status"] == "CALCULATED"
    assert c["Required residual-pressure head"]["status"] == "CALCULATED"
    assert r["pipe_sizing"]["selection_status"] == "SELECTED"
    assert c["Required booster head"]["status"] == "CALCULATED"
    assert c["Hydraulic power"]["status"] == "CALCULATED"

def test_booster_available_pressure_reduces_required_head():
    d = base()
    d["available_inlet_pressure"] = {"value": 0, "unit": "psi"}
    r0 = run_booster_design(d, rag_context={"velocity_criteria":{"max_mps":1.5}, "hazen_williams_c":140})
    d["available_inlet_pressure"] = {"value": 10, "unit": "psi"}
    r1 = run_booster_design(d, rag_context={"velocity_criteria":{"max_mps":1.5}, "hazen_williams_c":140})
    h0 = next(x["value"] for x in r0["calculations"] if x["name"]=="Required booster head")
    h1 = next(x["value"] for x in r1["calculations"] if x["name"]=="Required booster head")
    assert h1 < h0


def test_booster_elevation_uses_oht_source_level():
    d = base()
    d["oht_design_water_level"] = {"value": 100, "unit": "ft"}
    d["lowest_elevation_served"] = {"value": 110, "unit": "ft"}
    d["highest_elevation_served"] = {"value": 180, "unit": "ft"}
    r = run_booster_design(
        d,
        rag_context={"velocity_criteria":{"max_mps":1.5}, "hazen_williams_c":140}
    )
    elevation = next(x["value"] for x in r["calculations"] if x["name"]=="Elevation head")
    assert abs(elevation - (180-100)*0.3048) < 1e-12
