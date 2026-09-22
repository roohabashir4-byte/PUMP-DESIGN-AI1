# PumpDesign AI — Step 9

## Engineering Criteria + RAG → Calculation Interface

This package builds on Step 8 and freezes the production boundary:

**LLM reasoning/orchestration → RAG criteria → deterministic calculation tools**

The LLM can participate in engineering reasoning. Numerical truth remains deterministic.

### Included
- `models/engineering_contract.py` — typed boundary objects.
- `standards/criteria.py` — criterion validation/applicability.
- `standards/retrieval.py` — RAG-to-request boundary.
- `agent/tool_router.py` — deterministic tool execution boundary.
- `calculations/pipe_sizing.py` — hydraulic acceptance criteria now supported.
- `tests/test_step9_contract.py` — Step 9 contract tests.
- `STEP9_ENGINEERING_CRITERIA_INTERFACE.md` — frozen design rules.

### Test command

```bash
pytest -q
```

No new universal engineering criteria were invented in Step 9.
