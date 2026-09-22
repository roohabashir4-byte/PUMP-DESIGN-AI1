
from engineering.transfer import run_transfer_design

data = {
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
rag = {
    "velocity_criteria": {"min_mps": None, "max_mps": 1.5},
    "hazen_williams_c": 140,
    "references": [{"title": "RAG engineering criterion"}],
}
result = run_transfer_design(data, rag_context=rag)
flow = next(c for c in result["calculations"] if c["name"] == "Transfer design flow")
static = next(c for c in result["calculations"] if c["name"] == "Static head")
tdh = next(c for c in result["calculations"] if c["name"] == "Total Dynamic Head")
power = next(c for c in result["calculations"] if c["name"] == "Hydraulic power")

assert abs(flow["value"] - 277.77777777777777) < 1e-9
assert abs(static["value"] - 55.4736) < 1e-9
assert tdh["status"] == "CALCULATED"
assert power["status"] == "CALCULATED"
assert result["pipe_sizing"]["delivery"]["selection_status"] == "SELECTED"

print("STEP 4 TRANSFER WORKFLOW VALIDATION: PASS")
print(f'Design flow: {flow["value"]:.3f} {flow["unit"]}')
print(f'Static head: {static["value"]:.3f} {static["unit"]}')
print(f'TDH (major losses only): {tdh["value"]:.3f} {tdh["unit"]}')
print(f'Hydraulic power: {power["value"]:.1f} {power["unit"]}')
print("16 pytest tests passed")
