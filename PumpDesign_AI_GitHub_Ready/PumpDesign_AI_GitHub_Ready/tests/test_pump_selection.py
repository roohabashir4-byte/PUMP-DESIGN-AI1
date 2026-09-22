import pytest
from engineering.pump_selection import validate_commercial_pump, validate_curve_points


def duty(flow=100, head=40, npsha=None):
    d = {"flow": flow, "head": head}
    if npsha is not None:
        d["npsha"] = npsha
    return d


def curve():
    return {
        "manufacturer": "Example Manufacturer",
        "model": "Model X",
        "curve_source": "User-supplied manufacturer curve",
        "curve_points": [
            {"flow": 50, "head": 55, "efficiency": 0.65, "npshr": 2},
            {"flow": 100, "head": 45, "efficiency": 0.78, "npshr": 3},
            {"flow": 150, "head": 30, "efficiency": 0.74, "npshr": 5},
        ],
    }


def test_validates_duty_head_by_interpolation():
    r = validate_commercial_pump(duty(), curve())
    assert r["status"] == "PASS"
    assert r["interpolated_pump_performance"]["head"] == 45
    assert r["head_margin"] == 5
    assert r["selection_status"] == "COMMERCIAL_PUMP_CANDIDATE_VALIDATED"


def test_fails_when_pump_head_is_insufficient():
    r = validate_commercial_pump(duty(head=50), curve())
    assert r["status"] == "FAIL"
    assert r["selection_status"] == "COMMERCIAL_PUMP_NOT_SELECTED"


def test_fails_when_duty_flow_outside_curve():
    r = validate_commercial_pump(duty(flow=200), curve())
    assert r["status"] == "FAIL"
    assert "outside" in r["issues"][0]


def test_npsh_is_checked_only_when_both_values_exist():
    r = validate_commercial_pump(duty(npsha=4), curve())
    npsh = next(x for x in r["checks"] if x["name"] == "NPSH")
    assert npsh["status"] == "PASS"
    r2 = validate_commercial_pump(duty(npsha=2), curve())
    npsh2 = next(x for x in r2["checks"] if x["name"] == "NPSH")
    assert npsh2["status"] == "FAIL"


def test_missing_efficiency_is_not_invented():
    c = curve()
    for p in c["curve_points"]:
        p.pop("efficiency")
    r = validate_commercial_pump(duty(), c)
    eff = next(x for x in r["checks"] if x["name"] == "Efficiency")
    assert eff["status"] == "NOT_CHECKED"


def test_system_curve_intersection_is_reported_without_being_ranked():
    system = [(50, 30), (100, 45), (150, 60)]
    r = validate_commercial_pump(duty(), curve(), system_curve=system)
    assert r["operating_point"] is not None
    assert "best" in r["important_note"]


def test_duplicate_flow_is_rejected():
    with pytest.raises(ValueError):
        validate_curve_points([{"flow": 10, "head": 20}, {"flow": 10, "head": 19}])


def test_curve_units_are_converted_to_si():
    c = curve()
    c["flow_unit"] = "gpm"
    c["head_unit"] = "ft"
    c["npshr_unit"] = "ft"
    c["curve_points"] = [
        {"flow": 158.503, "head": 147.638, "efficiency": 0.78, "npshr": 9.843},
        {"flow": 317.006, "head": 131.234, "efficiency": 0.80, "npshr": 13.123},
    ]
    r = validate_commercial_pump({"flow": 0.01, "head": 40}, c)
    assert r["status"] == "PASS"


def test_motor_power_check_is_based_on_supplied_efficiency_without_safety_factor():
    c = curve()
    c["motor_power"] = 4.0
    c["motor_power_unit"] = "kW"
    d = duty()
    d["hydraulic_power"] = 3.0
    r = validate_commercial_pump(d, c)
    motor = next(x for x in r["checks"] if x["name"] == "Motor power")
    assert motor["status"] == "PASS"
