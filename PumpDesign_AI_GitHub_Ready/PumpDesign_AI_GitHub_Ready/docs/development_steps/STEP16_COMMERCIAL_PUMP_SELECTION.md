# Step 16 — Commercial Pump Selection & Pump-Curve Validation

## Purpose
Validate an actual user-supplied manufacturer pump curve against the deterministic PumpDesign duty point.

## Authority
- Deterministic workflow: authoritative design flow, required head, hydraulic power and available NPSHa when calculated.
- Manufacturer datasheet/curve: authoritative pump head curve, efficiency and NPSHr values.
- The LLM may explain and orchestrate the process but cannot invent manufacturer performance data.

## Validation performed
1. Manufacturer identity/model/source captured.
2. At least two pump-curve points required.
3. Curve points validated and sorted by flow.
4. Duty flow must fall inside the supplied curve range.
5. Pump head at duty flow is linearly interpolated.
6. Required head is compared with interpolated pump head.
7. Efficiency is interpolated when supplied.
8. Pump input/shaft power can be calculated from deterministic hydraulic power and supplied efficiency.
9. Manufacturer motor rating can be checked when supplied.
10. NPSHr is interpolated when supplied; it is compared with deterministic NPSHa only when NPSHa is available.
11. An optional pump/system curve intersection can be calculated when a system curve is supplied.

## Important engineering limits
- No universal pump efficiency is assumed.
- No NPSHr is invented.
- No NPSH safety margin is invented.
- No motor safety factor is invented.
- No pump is ranked as best/optimal.
- A validated candidate is not automatically presented as the final selected pump.
- Actual operating point is only reported when a pump curve and system curve intersection can be established.

## Curve data units
Supported manufacturer curve units:
- Flow: m³/s, L/s, gpm
- Head: m, ft
- NPSHr: m, ft
- Motor power: kW, hp

The validator converts manufacturer curve data to SI internally before comparison.

## UI
The Streamlit UI now provides a Commercial Pump Curve Validation section after a deterministic duty result is available. The engineer enters manufacturer data or pastes CSV curve points.

CSV columns:
`flow,head,efficiency,npshr`

Efficiency is entered as a fraction, e.g. `0.78`.

## Status
- `PASS`: supplied pump curve provides the required head at the duty flow and no supplied check fails.
- `FAIL`: supplied pump cannot satisfy the duty point or another supplied validation check fails.
- `NOT_CALCULABLE`: deterministic duty point is unavailable.
- `NOT_CHECKED`: optional manufacturer/system data required for a specific check were not supplied.

## Test result
59 tests pass.
