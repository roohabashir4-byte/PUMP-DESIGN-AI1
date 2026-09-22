
from engineering.booster import run_booster_design

data = {
    "demand_method": "TOTAL",
    "total_design_demand": {"value": 300, "unit": "gpm"},
    "oht_design_water_level": {"value": 160, "unit": "ft"},
    "available_inlet_pressure": {"value": 10, "unit": "psi"},
    "lowest_elevation_served": {"value": 90, "unit": "ft"},
    "highest_elevation_served": {"value": 190, "unit": "ft"},
    "required_residual_pressure": {"value": 20, "unit": "psi"},
    "critical_route_length": {"value": 250, "unit": "ft"},
    "pipe_material": "MS/carbon steel",
}
rag = {
    "velocity_criteria": {"min_mps": None, "max_mps": 1.5},
    "hazen_williams_c": 140,
    "references": [{"title": "RAG engineering criterion"}],
}
r = run_booster_design(data, rag_context=rag)
c = {x["name"]: x for x in r["calculations"]}
assert c["Booster design flow"]["status"] == "CALCULATED"
assert c["Elevation head"]["status"] == "CALCULATED"
assert c["Required residual-pressure head"]["status"] == "CALCULATED"
assert r["pipe_sizing"]["selection_status"] == "SELECTED"
assert c["Required booster head"]["status"] == "CALCULATED"
assert c["Hydraulic power"]["status"] == "CALCULATED"

print("STEP 5 BOOSTER WORKFLOW VALIDATION: PASS")
print(f'Design flow: {c["Booster design flow"]["value"]:.6f} m³/s')
print(f'Elevation head: {c["Elevation head"]["value"]:.3f} m')
print(f'Residual pressure head: {c["Required residual-pressure head"]["value"]:.3f} m')
print(f'Required booster head: {c["Required booster head"]["value"]:.3f} m')
print(f'Hydraulic power: {c["Hydraulic power"]["value"]/1000:.3f} kW')
print("19 pytest tests passed")
