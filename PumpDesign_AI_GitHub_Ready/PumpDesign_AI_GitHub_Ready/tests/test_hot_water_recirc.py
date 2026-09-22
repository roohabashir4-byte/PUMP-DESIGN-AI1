
from engineering.hot_water_recirc import run_hot_water_recirc_design

def rag():
    return {
        "heat_loss_rate_w_per_m": 30,
        "water_properties": {"density_kg_m3": 988, "cp_j_kgk": 4186.8},
        "velocity_criteria": {"min_mps": None, "max_mps": 1.5},
        "hazen_williams_c": 150,
        "references": [{"title":"ASHRAE test reference"}],
    }

def base():
    return {
        "system_arrangement":"CENTRAL_HEATER_VERTICAL_RISER",
        "hot_water_supply_temperature":{"value":60,"unit":"C"},
        "required_return_temperature":{"value":50,"unit":"C"},
        "total_hot_water_circulation_pipe_length":{"value":100,"unit":"m"},
        "pipe_material":"PP-R",
    }

def test_heat_loss_and_flow():
    r=run_hot_water_recirc_design(base(),rag_context=rag())
    c={x["name"]:x for x in r["calculations"]}
    assert c["Temperature difference"]["value"]==10
    assert c["Hot-water heat loss"]["value"]==3000
    expected=3000/(988*4186.8*10)
    assert abs(c["Recirculation design flow"]["value"]-expected)<1e-15
    assert c["Recirculation pump head"]["status"]=="CALCULATED"
    assert c["Hydraulic power"]["status"]=="CALCULATED"

def test_no_universal_heat_loss_assumption():
    r=run_hot_water_recirc_design(base(),rag_context={
        "water_properties":{"density_kg_m3":988,"cp_j_kgk":4186.8}
    })
    assert r["status"]=="NOT_CALCULABLE"
    c={x["name"]:x for x in r["calculations"]}
    assert c["Hot-water heat loss"]["status"]=="NOT_CALCULABLE"

def test_invalid_temperature_delta():
    d=base()
    d["required_return_temperature"]={"value":65,"unit":"C"}
    r=run_hot_water_recirc_design(d,rag_context=rag())
    assert r["status"]=="INVALID"

def test_fahrenheit_conversion():
    d=base()
    d["hot_water_supply_temperature"]={"value":140,"unit":"F"}
    d["required_return_temperature"]={"value":122,"unit":"F"}
    r=run_hot_water_recirc_design(d,rag_context=rag())
    c={x["name"]:x for x in r["calculations"]}
    assert abs(c["Temperature difference"]["value"]-10)<1e-12
