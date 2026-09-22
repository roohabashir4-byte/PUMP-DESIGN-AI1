# Step 15 — Pump Duty Point + Engineering Validation Layer

## Purpose
Normalize each deterministic pump workflow into a single engineering duty packet:

- design flow
- pump head / TDH
- hydraulic power
- optional input power when a valid efficiency is available
- validation status
- unresolved engineering items
- commercial pump selection status

## Authority
The deterministic workflow remains the numerical authority. This layer does not recalculate hydraulics. It extracts named deterministic results and classifies their completeness.

## Status meanings
- `DUTY_POINT_READY`: flow and required head are calculated and there are no warnings/failures.
- `PROVISIONAL`: flow and head are calculated, but validation warnings or other non-final conditions remain.
- `NOT_CALCULABLE`: required deterministic flow/head is unavailable.
- `INCOMPLETE`: a required duty result is absent even though the workflow did not explicitly report missing input.
- `INVALID`: unsupported application or invalid result condition.

## Validation
Critical failures and warnings are preserved. A warning such as missing minor losses prevents a result from being presented as a final duty point; it remains a usable provisional calculation with unresolved items.

## Commercial pump selection
Step 15 does not select a manufacturer pump. The output remains `COMMERCIAL_PUMP_NOT_SELECTED`. Manufacturer pump curves, efficiency, NPSHr, operating point and related selection checks belong to a later commercial-selection stage.

## Application mapping
- Transfer: `Transfer design flow` + `Total Dynamic Head`
- Booster: `Booster design flow` + `Required booster head`
- Submersible: `Submersible design flow` + `Total Dynamic Head`
- Hot-water recirculation: `Recirculation design flow` + `Recirculation pump head`

## Test result
50 tests pass.
