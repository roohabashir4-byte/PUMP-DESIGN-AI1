# Step 10 — LLM Agent + Tool Router

## Purpose

Connect the frozen Step 9 boundary to a real LLM orchestration loop:

**User/project context → LLM reasoning → RAG criteria → deterministic workflow → LLM interpretation**

## What the agent can do

- classify transfer, booster, submersible, and hot-water recirculation scenarios;
- request applicable engineering criteria from the injected RAG retriever;
- refuse to run a deterministic workflow before criteria retrieval;
- call exactly one of the four deterministic design workflows as required;
- pass the workflow result back to the LLM for explanation;
- preserve warnings, missing inputs, and source references.

## Numerical authority

The LLM never becomes the numerical authority. The deterministic workflow remains the source of numerical design results.

## RAG interface

The agent accepts an injected callable:

`rag_retriever(application=..., service=..., jurisdiction=...)`

It may return either `Criterion` objects or dictionaries compatible with the Step 9 `Criterion` model.

This keeps the agent independent of the eventual FAISS/RAG implementation.

## Groq

The default provider is Groq using the model from `GROQ_MODEL`, defaulting to the project's configured Qwen model. `GROQ_API_KEY` is required when the real agent is executed.

## Tool order

The agent is instructed and enforced to retrieve RAG criteria before running a design workflow.

## Important production note

The four existing engineering workflows remain the deterministic layer from Steps 4–8. Step 10 does not invent new engineering criteria. Any unresolved engineering limitation already identified in the audit remains unresolved until its corresponding criteria/data are supplied.

## Test

`pytest -q` → 38 tests passed.
