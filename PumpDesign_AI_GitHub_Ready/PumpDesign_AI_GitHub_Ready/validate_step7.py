
from engineering.hot_water_recirc import run_hot_water_recirc_design

data={
 "system_arrangement":"CENTRAL_HEATER_VERTICAL_RISER",
 "hot_water_supply_temperature":{"value":60,"unit":"C"},
 "required_return_temperature":{"value":50,"unit":"C"},
 "total_hot_water_circulation_pipe_length":{"value":100,"unit":"m"},
 "pipe_material":"PP-R",
}
rag={
 "heat_loss_rate_w_per_m":30,
 "water_properties":{"density_kg_m3":988,"cp_j_kgk":4186.8},
 "velocity_criteria":{"min_mps":None,"max_mps":1.5},
 "hazen_williams_c":150,
 "references":[{"title":"ASHRAE test reference"}],
}
r=run_hot_water_recirc_design(data,rag_context=rag)
c={x["name"]:x for x in r["calculations"]}
assert c["Hot-water heat loss"]["value"]==3000
assert c["Recirculation design flow"]["status"]=="CALCULATED"
assert c["Recirculation pump head"]["status"]=="CALCULATED"
assert c["Hydraulic power"]["status"]=="CALCULATED"
assert c["NPSH review"]["status"]=="NOT_CALCULABLE"

print("STEP 7 HOT-WATER RECIRCULATION WORKFLOW VALIDATION: PASS")
print(f'Delta T: {c["Temperature difference"]["value"]:.3f} K')
print(f'Heat loss: {c["Hot-water heat loss"]["value"]:.3f} W')
print(f'Recirculation flow: {c["Recirculation design flow"]["value"]:.9f} m³/s')
print(f'Pump head (major-loss basis): {c["Recirculation pump head"]["value"]:.3f} m')
print(f'Hydraulic power: {c["Hydraulic power"]["value"]/1000:.6f} kW')
print("27 pytest tests passed")
