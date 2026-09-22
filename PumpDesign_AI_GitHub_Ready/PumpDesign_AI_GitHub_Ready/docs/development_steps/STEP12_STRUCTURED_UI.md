# Step 12 — Structured PumpDesign AI UI

## Purpose

Connect the frozen PumpDesign AI structured inputs to the Step 10 LLM agent and Step 11 local RAG store without changing engineering calculation ownership.

## Workflow

User structured inputs → LLM agent → applicable RAG criteria → deterministic engineering workflow → deterministic result → LLM explanation.

## Supported applications

1. Transfer Pump — UGT → OHT
2. Booster Pump
3. Submersible Pump
4. Hot-Water Recirculation Pump

## UI rules

- Structured fields are used instead of one large engineering text box.
- Units are explicit for numerical inputs.
- Unknown values can remain unknown.
- The application does not fabricate missing engineering values.
- A custom-scenario field is available for each application.
- Retrieved RAG criteria are visible after a successful agent run.
- The deterministic workflow remains the numerical authority.
- Commercial pump selection is not claimed unless manufacturer data exists.

## Step 12 scope

This step implements the design-entry UI and end-to-end connection to the existing agent/RAG/calculation stack. Persistent project memory, revisions, formal calculation reports, manufacturer pump selection and production deployment hardening remain separate implementation stages.
