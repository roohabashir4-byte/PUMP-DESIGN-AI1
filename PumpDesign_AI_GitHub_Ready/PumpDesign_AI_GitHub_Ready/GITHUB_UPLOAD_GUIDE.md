# PumpDesign AI — GitHub Upload Guide

This is the cumulative Step 17 repository. Steps 1–17 are already integrated into one project; they are not separate applications.

## Upload

Upload the contents of this folder to the root of the new GitHub repository.

## Streamlit entry point

`app.py`

## Python dependencies

`requirements.txt`

## Engineering code

- `calculations/` — deterministic numerical calculations
- `engineering/` — pump application workflows
- `standards/` — criteria and RAG retrieval
- `agent/` — LLM orchestration and tool routing
- `memory/` — structured project/design memory
- `reports/` — calculation and reference reporting
- `models/` — structured data models
- `data/` — engineering/RAG knowledge data
- `tests/` — automated tests

## Important

API keys must be supplied through Streamlit Cloud Secrets and must not be committed to GitHub.
