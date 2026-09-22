"""Quick validation runner for Step 2."""
from calculations.demand import transfer_flow
from calculations.hydraulics import hazen_williams_head_loss, velocity
from calculations.units import gpm_to_m3s

q = transfer_flow(25000, 90).flow
q_si = gpm_to_m3s(q)
loss = hazen_williams_head_loss(q_si, 0.1524, 61.0, 140).value
vel = velocity(q_si, 0.1524).value
assert q > 0 and loss > 0 and vel > 0
print("STEP 2 CALCULATION ENGINE VALIDATION: PASS")
print(f"Transfer flow: {q:.3f} US gpm")
print(f"Velocity example: {vel:.3f} m/s")
print(f"Hazen-Williams loss example: {loss:.3f} m")
