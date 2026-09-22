# Step 9 — Engineering Criteria + RAG → Calculation Interface

## Purpose

This step freezes the boundary between three layers:

1. **LLM** — engineering reasoning, workflow selection, missing-input detection, method selection, explanation, and orchestration.
2. **RAG** — applicable engineering knowledge, criteria, source metadata, and method permissions.
3. **Deterministic tools** — numerical calculations and numerical validation.

The LLM is allowed to reason about engineering concepts. It is **not** the authoritative source of a numerical design result.

## Frozen contract

### LLM may
- classify the pump application/scenario;
- identify required inputs and derivable inputs;
- choose between supported engineering workflows;
- request applicable RAG criteria;
- choose a hydraulic method when supported by retrieved criteria;
- decide which deterministic tool is required;
- interpret tool results and identify follow-up information;
- explain assumptions, warnings, limitations, and revisions.

### RAG must provide
- criterion value/range and unit;
- application/service/jurisdiction applicability;
- source reference ID and source status;
- edition/year, section/page where available;
- method or basis where relevant.

RAG retrieval must not silently turn an unrelated or generic criterion into a project criterion.

### Deterministic tools must own
- unit conversion used in calculations;
- pipe geometry and hydraulic calculations;
- flow/head/power/NPSH numerical results;
- validation against explicit criteria;
- authoritative numerical result returned to the report.

## Pipe selection rule added in Step 9

A velocity calculation alone is not enough to make the final automatic pipe-size decision.

The sizing engine now supports a RAG-supplied hydraulic acceptance criterion:
- maximum total head loss, **or**
- maximum head loss per 100 m.

If a head loss is merely calculated but no acceptance limit is supplied, the engine will **not** select a pipe from that result. This prevents an undocumented engineering decision.

No universal friction-loss limit has been invented in this step.

## Water-property rule

Water properties that materially affect a calculation should be carried explicitly through the calculation request when needed. Hidden defaults remain legacy calculation-engine behavior and are not treated as project-specific criteria.

For hot-water calculations, temperature-dependent density/specific heat must come from the applicable RAG/source basis already required by that workflow.

## Missing-data rule

If a required engineering criterion or numerical input is unavailable:
- return `MISSING_INPUT` or `NOT_CALCULABLE` as appropriate;
- state exactly what is missing;
- do not fabricate a value;
- do not silently substitute a generic engineering value.

## Conflicting criteria

If multiple applicable criteria match the same parameter, the RAG layer must preserve both and the agent must resolve source precedence/applicability before calculation. The interface deliberately raises an error rather than choosing one silently.

## Calculation provenance

Every calculation request carries:
- request ID;
- application;
- tool name;
- numerical inputs;
- source type for inputs;
- criterion IDs;
- method decision;
- water properties when required;
- purpose.

Every result carries:
- status;
- value/unit;
- formula where available;
- substituted values;
- method;
- assumptions/warnings;
- criterion/reference IDs;
- `DETERMINISTIC_TOOL` as the authoritative numeric source.

## What is intentionally not frozen here

This step does **not** invent universal values for:
- allowable velocity;
- allowable friction/head loss;
- fitting/valve K values;
- demand/peak-flow factors;
- water properties for every temperature;
- pump efficiency;
- NPSHR;
- hot-water heat-loss rates.

Those must come from the applicable RAG/source, manufacturer data, project criteria, or an explicit engineer override.
