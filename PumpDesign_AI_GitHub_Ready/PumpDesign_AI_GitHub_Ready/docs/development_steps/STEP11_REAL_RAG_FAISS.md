# Step 11 — Real RAG / FAISS Knowledge Base

The agent is now connected to the actual PumpDesign AI knowledge pack.

## Included knowledge
- BCP 2021
- IPC 2021 Chapter 6
- IPC Appendix E applicability
- ASHRAE Fundamentals 2025 fluid-flow / pipe-design summaries
- ASHRAE HVAC Applications 2023 hot-water recirculation summaries
- PumpDesign engineering criteria
- Extended engineering criteria registry
- Hazen-Williams C registry
- Pipe registry/dimensions

## Retrieval
`standards.rag_store.RAGStore` loads the packaged corpus and criteria and provides the callable retriever expected by Step 10.

FAISS is the production vector-index option. The build script uses the same TF-IDF vector representation to create a FAISS inner-product index when `faiss-cpu` is installed. Local validation in this environment uses the deterministic TF-IDF fallback because external package installation is unavailable.

## Run
```bash
python -m standards.build_index
```

Then construct the agent with:
```python
from standards.rag_store import RAGStore
from agent.agent import PumpDesignAgent

store = RAGStore()
agent = PumpDesignAgent(rag_retriever=store.retriever)
```

The agent now retrieves actual packaged criteria before deterministic design calculations.
