from pathlib import Path

from standards.rag_store import RAGStore


def test_rag_store_loads_real_knowledge_pack():
    store = RAGStore()
    assert len(store.chunks) == 13
    assert len(store.criteria) >= 8
    assert "BCP-2021" in store.sources


def test_retrieve_booster_returns_applicable_criteria():
    store = RAGStore()
    criteria = store.retrieve_criteria(application="BOOSTER", query="booster source pressure elevation critical fixture")
    ids = {c.criterion_id for c in criteria}
    assert "IPC-BOOST-003" in ids or "IPC-WTR-003" in ids


def test_retrieve_hazen_williams_registry_criterion():
    store = RAGStore()
    criteria = store.retrieve_criteria(application="TRANSFER", query="Hazen Williams C MS steel")
    assert any(c.parameter == "hazen_williams_c" for c in criteria)

def test_agent_rag_can_target_pipe_material():
    store = RAGStore()
    from agent.agent import PumpDesignAgent
    agent = PumpDesignAgent(rag_retriever=store.retriever, api_key="dummy")
    ctx = agent._rag_tool({"application": "transfer", "service": "water", "jurisdiction": "Pakistan", "material": "MS/carbon steel", "query": "Hazen Williams C"})
    assert ctx["hazen_williams_c"] is not None
