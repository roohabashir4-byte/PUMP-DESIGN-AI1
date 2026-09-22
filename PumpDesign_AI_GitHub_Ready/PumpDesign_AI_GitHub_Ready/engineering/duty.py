"""Normalize pump-workflow results into an engineering duty/validation packet.

This layer does not perform hydraulic calculations. It extracts deterministic
results, applies explicit completeness rules, and clearly separates a usable
duty point from a provisional calculation or a non-calculable design.
"""
from __future__ import annotations

from typing import Any


_APPLICATIONS = {
    "TRANSFER_PUMP": {"flow": "Transfer design flow", "head": "Total Dynamic Head"},
    "BOOSTER_PUMP": {"flow": "Booster design flow", "head": "Required booster head"},
    "SUBMERSIBLE_PUMP": {"flow": "Submersible design flow", "head": "Total Dynamic Head"},
    "HOT_WATER_RECIRCULATION_PUMP": {"flow": "Recirculation design flow", "head": "Recirculation pump head"},
}


def _find(calculations: list[dict], name: str) -> dict | None:
    for item in calculations:
        if item.get("name") == name:
            return item
    return None


def _numeric(item: dict | None) -> float | None:
    if not item or item.get("status") != "CALCULATED":
        return None
    value = item.get("value")
    return value if isinstance(value, (int, float)) else None


def _validation_summary(validation: list[dict]) -> tuple[str, list[str]]:
    unresolved: list[str] = []
    has_critical = False
    has_fail = False
    has_warning = False
    for item in validation:
        status = str(item.get("status", "")).upper()
        severity = str(item.get("severity", "")).upper()
        message = item.get("message") or item.get("name") or "Unspecified validation issue"
        if status == "FAIL" or severity == "CRITICAL":
            has_critical = True
            unresolved.append(message)
        elif status == "WARNING" or severity == "WARNING":
            has_warning = True
            unresolved.append(message)
    if has_critical or has_fail:
        return "FAIL", unresolved
    if has_warning:
        return "WARNING", unresolved
    return "PASS", unresolved


def build_pump_duty(result: dict[str, Any]) -> dict[str, Any]:
    """Build the authoritative duty/validation packet from a workflow result."""
    application = result.get("application")
    rule = _APPLICATIONS.get(application)
    if not rule:
        return {
            "status": "INVALID",
            "validation_status": "FAIL",
            "message": f"Unsupported pump application: {application}",
            "commercial_selection_status": "COMMERCIAL_PUMP_NOT_SELECTED",
        }

    calculations = result.get("calculations", [])
    flow_calc = _find(calculations, rule["flow"])
    head_calc = _find(calculations, rule["head"])
    hydraulic_calc = _find(calculations, "Hydraulic power")
    input_calc = _find(calculations, "Pump input power")

    flow = _numeric(flow_calc)
    head = _numeric(head_calc)
    hydraulic_power = _numeric(hydraulic_calc)
    input_power = _numeric(input_calc)

    validation_status, unresolved = _validation_summary(result.get("validation", []))

    # Missing/invalid calculations override a validation PASS because a duty
    # point cannot be issued without the required deterministic outputs.
    if flow is None or head is None:
        overall = "NOT_CALCULABLE" if result.get("status") in {"NOT_CALCULABLE", "MISSING_INPUT"} else "INCOMPLETE"
        validation_status = "FAIL" if result.get("status") == "INVALID" else validation_status
        unresolved.insert(0, "Required design flow and/or pump head was not deterministically calculated.")
    elif validation_status == "FAIL":
        overall = "PROVISIONAL"
    elif validation_status == "WARNING" or result.get("status") != "CALCULATED":
        overall = "PROVISIONAL"
    else:
        overall = "DUTY_POINT_READY"

    # A warning such as missing minor losses means the numerical head is useful
    # but must not be presented as a final issue-for-construction duty point.
    return {
        "status": overall,
        "validation_status": validation_status,
        "flow": flow,
        "flow_unit": flow_calc.get("unit") if flow_calc else None,
        "head": head,
        "head_unit": head_calc.get("unit") if head_calc else None,
        "hydraulic_power": hydraulic_power,
        "hydraulic_power_unit": hydraulic_calc.get("unit") if hydraulic_calc else None,
        "input_power": input_power,
        "input_power_unit": input_calc.get("unit") if input_calc else None,
        "commercial_selection_status": "COMMERCIAL_PUMP_NOT_SELECTED",
        "basis": {
            "flow_calculation": rule["flow"],
            "head_calculation": rule["head"],
            "power_calculation": "Hydraulic power",
        },
        "unresolved_items": list(dict.fromkeys(unresolved)),
    }


def attach_pump_duty(result: dict[str, Any]) -> dict[str, Any]:
    """Return the workflow result with a normalized pump duty packet attached."""
    result = dict(result)
    result["pump_duty"] = build_pump_duty(result)
    return result
