"""Step 17 no-network end-to-end integration smoke test."""
from pathlib import Path
import tempfile

from standards.rag_store import RAGStore
from engineering.transfer import run_transfer_design
from reports.calculation_report import build_report_payload, generate_pdf


def main():
    store = RAGStore(top_k=6)
    criteria = store.retrieve_criteria(
        application="TRANSFER",
        jurisdiction="Pakistan",
        query="transfer pump pipe velocity Hazen Williams steel",
    )
    assert criteria, "RAG returned no criteria"

    rag = {
        "references": sorted({c.source_reference_id for c in criteria}),
        "criteria": [c.model_dump(mode="json") for c in criteria],
        "velocity_criteria": {"max_mps": 3.0},
        "hazen_williams_c": 140.0,
    }
    result = run_transfer_design({
        "oht_capacity": {"value": 25000, "unit": "US gal"},
        "required_transfer_time": {"value": 90, "unit": "min"},
        "ugt_design_water_level": {"value": -22, "unit": "ft"},
        "oht_design_water_level": {"value": 160, "unit": "ft"},
        "suction_pipe_length": {"value": 20, "unit": "ft"},
        "delivery_pipe_length": {"value": 200, "unit": "ft"},
        "pipe_material": "MS/carbon steel",
    }, rag_context=rag)
    assert result["pump_duty"]["flow"] is not None
    assert result["pump_duty"]["head"] is not None

    payload = build_report_payload(
        design_id="step17-smoke",
        application="TRANSFER",
        inputs={"project_name": "Step 17 Smoke Test", "location": "Pakistan", "building_type": "Test"},
        result=result,
        rag_context=rag,
        project={"project_name": "Step 17 Smoke Test", "location": "Pakistan", "building_type": "Test"},
    )
    assert payload["result"]["pump_duty"]["flow"] is not None

    with tempfile.TemporaryDirectory() as td:
        pdf = generate_pdf(payload, Path(td) / "step17_smoke.pdf")
        assert pdf.exists() and pdf.stat().st_size > 0

    print("STEP17_SMOKE_PASS")
    print(f"RAG criteria: {len(criteria)}")
    print(f"Duty flow: {result['pump_duty']['flow']} {result['pump_duty']['flow_unit']}")
    print(f"Duty head: {result['pump_duty']['head']} {result['pump_duty']['head_unit']}")


if __name__ == "__main__":
    main()
