from calculations.pipe_sizing import PipeRegistry, size_pipe_candidates, select_first_acceptable
from calculations.units import M3S_PER_GPM

reg = PipeRegistry()
assert len(reg.records) > 100
q = 277.7777778 * M3S_PER_GPM
candidates = size_pipe_candidates(q, "MS/carbon steel", velocity_max_mps=2.0)
selected = select_first_acceptable(candidates)
assert selected is not None
print("STEP 3 PIPE REGISTRY + SIZING VALIDATION: PASS")
print(f"Registry records: {len(reg.records)}")
print(f"Candidates for transfer example: {len(candidates)}")
print(f"Selected candidate: {selected.pipe.size_label}, {selected.pipe.schedule_or_sdr}")
print(f"Actual ID: {selected.pipe.inside_diameter_m*1000:.2f} mm")
print(f"Velocity: {selected.velocity_mps:.3f} m/s")
