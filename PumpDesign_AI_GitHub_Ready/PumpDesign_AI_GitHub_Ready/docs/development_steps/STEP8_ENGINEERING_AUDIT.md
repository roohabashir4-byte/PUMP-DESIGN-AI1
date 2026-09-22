# PumpDesign AI — Step 8 Engineering Audit

## Scope
Audit of the four deterministic pump application workflows delivered in Steps 4–7:
Transfer, Booster, Submersible, and Hot-Water Recirculation.

## Findings

### 1. Booster source-elevation calculation — FIXED
**Severity:** Critical design-logic issue.

The previous booster workflow calculated elevation head as:

`Zhighest served - Zlowest served`

That is not the correct source-to-critical-point elevation basis when the frozen design source is the OHT/source water level.

It is now:

`He = Zhighest served - ZOHT/source`

The lowest served elevation is retained for later pressure/zone validation and is not substituted for the hydraulic source.

A regression test was added.

### 2. Pipe-size automatic selection — DESIGN LIMITATION, NOT FABRICATED
**Severity:** High / requires engineering criterion.

All four workflows currently use the smallest candidate satisfying the supplied velocity criterion.

This is deterministic, but it is **not sufficient as a universal final pipe-selection rule**. Pipe selection may also require:
- allowable velocity for the specific service,
- allowable friction/head-loss criterion,
- pressure/operating constraints,
- suction-specific constraints,
- project/AHJ criteria,
- practical/commercial size constraints.

The engine therefore must not silently claim that the selected pipe is the universally optimal size.

For now, the selection remains explicitly labelled as:
**smallest candidate satisfying the supplied velocity criterion**.

The next engineering-data/criteria stage should add an explicit head-loss/friction criterion or another documented selection rule before final production pipe selection is frozen.

### 3. Minor losses — correctly not invented
**Status:** Accepted limitation.

Fittings and valves are not frozen UI inputs. The workflows do not fabricate K values. TDH/pump head is clearly marked provisional when only major straight-pipe loss is available.

### 4. NPSH — correctly separated
**Status:** Accepted.

NPSHa is system-derived. NPSHr must come from the actual selected pump manufacturer. The workflows do not invent NPSHr.

### 5. Transfer flow basis — accepted
Transfer flow is derived from the finalized full-fill OHT capacity basis and required transfer time. Daily demand may be calculated for context but is not silently converted into transfer pump flow.

### 6. Submersible source-capacity check — accepted
For tube wells, dynamic water level is used as the pumping source level. Well yield is treated as a source-capacity limit, not as a water-level input. If yield is missing, no yield is assumed.

### 7. Hot-water recirculation flow basis — accepted
Recirculation flow is based on pipe heat loss:

`q_total = q' × L`

`Q = q_total / (rho × cp × Delta T)`

A universal W/m heat-loss value is not embedded. The heat-loss criterion and water properties must come from the engineering/RAG layer.

### 8. Numerical calculation ownership — accepted
The deterministic calculation modules own numerical results. The LLM may choose workflow, methodology, applicable RAG criteria, missing-information questions, and tool calls, but numerical truth remains in deterministic tools.

## Audit conclusion

The four workflows are suitable as deterministic engineering workflow foundations after the booster source-elevation correction.

They are **not yet frozen as final engineering design software** because pipe selection still needs a documented selection criterion beyond velocity alone, and final system losses may require fittings/valves/branch data.

No missing engineering value should be invented to make a calculation complete.

## Test status

All automated tests pass after the correction.
