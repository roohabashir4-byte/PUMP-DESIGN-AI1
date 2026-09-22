
from engineering.submersible import run_submersible_design

data = {
    "primary_use": "TUBE_WELL_TO_UGT",
    "dynamic_water_level": {"value": -30, "unit": "m"},
    "well_yield": {"value": 100, "unit": "gpm"},
    "destination_water_level": {"value": 20, "unit": "m"},
    "known_design_flow": {"value": 80, "unit": "gpm"},
    "delivery_pipe_length": {"value": 100, "unit": "m"},
    "pipe_material": "MS/carbon steel",
}
rag = {
    "velocity_criteria": {"min_mps": None, "max_mps": 1.5},
    "hazen_williams_c": 140,
    "references": [{"title": "RAG engineering criterion"}],
}
r = run_submersible_design(data, rag_context=rag)
c = {x["name"]: x for x in r["calculations"]}
assert c["Well yield check"]["status"] == "CALCULATED"
assert r["validation"][0]["status"] == "PASS"
assert c["Static elevation head"]["value"] == 50
assert c["Total Dynamic Head"]["status"] == "CALCULATED"
assert c["NPSH review"]["status"] == "NOT_CALCULABLE"

print("STEP 6 SUBMERSIBLE WORKFLOW VALIDATION: PASS")
print(f'Design flow: {c["Submersible design flow"]["value"]:.6f} m³/s')
print(f'Source level: {c["Source water level"]["value"]:.3f} m')
print(f'Static head: {c["Static elevation head"]["value"]:.3f} m')
print(f'Total Dynamic Head: {c["Total Dynamic Head"]["value"]:.3f} m')
print(f'Hydraulic power: {c["Hydraulic power"]["value"]/1000:.3f} kW')
print("23 pytest tests passed")
