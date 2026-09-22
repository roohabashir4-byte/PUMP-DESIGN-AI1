from engineering.duty import build_pump_duty, attach_pump_duty


def calc(name, value, unit="m"):
    return {"name": name, "status": "CALCULATED", "value": value, "unit": unit}


def test_transfer_duty_ready_when_complete_and_no_warnings():
    r = {
        "application": "TRANSFER_PUMP",
        "status": "CALCULATED",
        "calculations": [calc("Transfer design flow", 0.01, "m³/s"), calc("Total Dynamic Head", 50, "m"), calc("Hydraulic power", 4.9, "kW")],
        "validation": [],
    }
    d = build_pump_duty(r)
    assert d["status"] == "DUTY_POINT_READY"
    assert d["validation_status"] == "PASS"
    assert d["flow"] == 0.01
    assert d["head"] == 50
    assert d["hydraulic_power"] == 4.9
    assert d["commercial_selection_status"] == "COMMERCIAL_PUMP_NOT_SELECTED"


def test_warning_makes_duty_provisional():
    r = {
        "application": "SUBMERSIBLE_PUMP",
        "status": "CALCULATED",
        "calculations": [calc("Submersible design flow", 0.005, "m³/s"), calc("Total Dynamic Head", 52, "m"), calc("Hydraulic power", 2.55, "kW")],
        "validation": [{"name": "TDH completeness", "status": "WARNING", "severity": "WARNING", "message": "Minor losses missing."}],
    }
    d = build_pump_duty(r)
    assert d["status"] == "PROVISIONAL"
    assert d["validation_status"] == "WARNING"
    assert "Minor losses missing." in d["unresolved_items"]


def test_missing_head_prevents_duty_point():
    r = {
        "application": "BOOSTER_PUMP",
        "status": "MISSING_INPUT",
        "calculations": [calc("Booster design flow", 0.01, "m³/s")],
        "validation": [],
    }
    d = build_pump_duty(r)
    assert d["status"] == "NOT_CALCULABLE"
    assert d["head"] is None
    assert d["validation_status"] == "PASS"
    assert d["unresolved_items"]


def test_critical_validation_prevents_ready_status():
    r = {
        "application": "HOT_WATER_RECIRCULATION_PUMP",
        "status": "CALCULATED",
        "calculations": [calc("Recirculation design flow", 0.00007, "m³/s"), calc("Recirculation pump head", 3, "m"), calc("Hydraulic power", 0.002, "kW")],
        "validation": [{"name": "Temperature", "status": "FAIL", "severity": "CRITICAL", "message": "Invalid temperature basis."}],
    }
    d = build_pump_duty(r)
    assert d["status"] == "PROVISIONAL"
    assert d["validation_status"] == "FAIL"


def test_attach_preserves_raw_result():
    r = {"application": "BOOSTER_PUMP", "status": "CALCULATED", "calculations": [], "validation": []}
    out = attach_pump_duty(r)
    assert out["application"] == "BOOSTER_PUMP"
    assert "pump_duty" in out
