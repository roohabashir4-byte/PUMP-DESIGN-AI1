
from engineering.submersible import run_submersible_design

def rag():
    return {
        "velocity_criteria": {"min_mps": None, "max_mps": 1.5},
        "hazen_williams_c": 140,
        "references": [{"title": "test criterion"}],
    }

def base():
    return {
        "primary_use": "TUBE_WELL_TO_UGT",
        "dynamic_water_level": {"value": -30, "unit": "m"},
        "well_yield": {"value": 100, "unit": "gpm"},
        "destination_water_level": {"value": 20, "unit": "m"},
        "known_design_flow": {"value": 80, "unit": "gpm"},
        "delivery_pipe_length": {"value": 100, "unit": "m"},
        "pipe_material": "MS/carbon steel",
    }

def test_tube_well_uses_dynamic_level_and_checks_yield():
    r=run_submersible_design(base(), rag_context=rag())
    c={x["name"]:x for x in r["calculations"]}
    assert c["Source water level"]["value"] == -30
    assert c["Well yield check"]["status"]=="CALCULATED"
    assert r["validation"][0]["status"]=="PASS"
    assert c["Static elevation head"]["value"] == 50
    assert c["Total Dynamic Head"]["status"]=="CALCULATED"
    assert c["NPSH review"]["status"]=="NOT_CALCULABLE"

def test_well_yield_failure_is_flagged():
    d=base()
    d["known_design_flow"]={"value":120,"unit":"gpm"}
    r=run_submersible_design(d, rag_context=rag())
    assert any(v["name"]=="Well yield capacity" and v["status"]=="FAIL" for v in r["validation"])

def test_sump_scenario_does_not_require_well_yield():
    d=base()
    d["primary_use"]="SUMP_TO_OHT"
    d.pop("dynamic_water_level")
    d.pop("well_yield")
    d["sump_water_level"]={"value":-5,"unit":"m"}
    d["destination_water_level"]={"value":35,"unit":"m"}
    r=run_submersible_design(d, rag_context=rag())
    c={x["name"]:x for x in r["calculations"]}
    assert c["Source water level"]["status"]=="CALCULATED"
    assert not any(x["name"]=="Well yield check" for x in r["calculations"])
    assert c["Static elevation head"]["value"]==40

def test_filling_time_flow():
    d=base()
    d.pop("known_design_flow")
    d["destination_capacity"]={"value":20000,"unit":"US gal"}
    d["required_filling_time"]={"value":60,"unit":"min"}
    r=run_submersible_design(d, rag_context=rag())
    c={x["name"]:x for x in r["calculations"]}
    assert abs(c["Submersible design flow"]["value"]-0.021030065466666668) < 1e-9
