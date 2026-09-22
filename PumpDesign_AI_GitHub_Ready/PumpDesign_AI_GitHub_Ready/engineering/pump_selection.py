"""Commercial pump curve validation.

This module does not choose a "best" pump. It validates a user-supplied
manufacturer pump curve against an already-calculated deterministic duty
point. Manufacturer data remains the source of truth for pump performance,
efficiency and NPSHr.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from calculations.units import gpm_to_m3s, ft_to_m


@dataclass(frozen=True)
class CurvePoint:
    flow: float
    head: float
    efficiency: float | None = None
    npshr: float | None = None


def _interp(points: list[CurvePoint], x: float, attr: str) -> float | None:
    if not points or x < points[0].flow or x > points[-1].flow:
        return None
    for p in points:
        if x == p.flow:
            return getattr(p, attr)
    for a, b in zip(points, points[1:]):
        if a.flow <= x <= b.flow:
            av = getattr(a, attr)
            bv = getattr(b, attr)
            if av is None or bv is None:
                return None
            if b.flow == a.flow:
                return av
            ratio = (x - a.flow) / (b.flow - a.flow)
            return av + ratio * (bv - av)
    return None


def validate_curve_points(points: list[dict[str, Any]]) -> list[CurvePoint]:
    if len(points) < 2:
        raise ValueError("At least two manufacturer pump-curve points are required.")
    parsed: list[CurvePoint] = []
    for i, raw in enumerate(points, 1):
        try:
            flow = float(raw["flow"])
            head = float(raw["head"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"Curve point {i} requires numeric flow and head.") from exc
        if flow < 0 or head < 0:
            raise ValueError(f"Curve point {i} cannot have negative flow or head.")
        efficiency = raw.get("efficiency")
        if efficiency is not None:
            efficiency = float(efficiency)
            if not 0 < efficiency <= 1:
                raise ValueError(f"Curve point {i} efficiency must be >0 and <=1 as a fraction.")
        npshr = raw.get("npshr")
        if npshr is not None:
            npshr = float(npshr)
            if npshr < 0:
                raise ValueError(f"Curve point {i} NPSHr cannot be negative.")
        parsed.append(CurvePoint(flow, head, efficiency, npshr))
    parsed.sort(key=lambda p: p.flow)
    if any(a.flow == b.flow for a, b in zip(parsed, parsed[1:])):
        raise ValueError("Manufacturer curve cannot contain duplicate flow values.")
    return parsed


def _system_intersection(
    pump: list[CurvePoint], system_points: list[tuple[float, float]]
) -> dict[str, float] | None:
    if len(system_points) < 2:
        return None
    syspts = sorted((float(q), float(h)) for q, h in system_points)
    candidates: list[tuple[float, float]] = []
    # Build common flow intervals and find sign changes of pump-head minus system-head.
    flows = sorted({q for q, _ in syspts} | {p.flow for p in pump})
    if len(flows) < 2:
        return None

    def sys_h(q: float) -> float | None:
        for q0, h0 in syspts:
            if q == q0:
                return h0
        for (q0, h0), (q1, h1) in zip(syspts, syspts[1:]):
            if q0 <= q <= q1:
                return h0 + (q - q0) * (h1 - h0) / (q1 - q0)
        return None

    def pump_h(q: float) -> float | None:
        return _interp(pump, q, "head")

    valid = []
    for q in flows:
        ph, sh = pump_h(q), sys_h(q)
        if ph is not None and sh is not None:
            valid.append((q, ph - sh))
    for (q0, d0), (q1, d1) in zip(valid, valid[1:]):
        if d0 == 0:
            return {"flow": q0, "head": pump_h(q0) or 0.0}
        if d0 * d1 < 0:
            q = q0 + (q1 - q0) * (-d0) / (d1 - d0)
            h = pump_h(q)
            if h is not None:
                candidates.append((q, h))
    if valid and valid[-1][1] == 0:
        candidates.append((valid[-1][0], pump_h(valid[-1][0]) or 0.0))
    if not candidates:
        return None
    q, h = candidates[0]
    return {"flow": q, "head": h}


def _flow_to_si(value: float, unit: str) -> float:
    u = unit.strip().lower()
    if u in {"m³/s", "m3/s"}:
        return value
    if u in {"l/s", "lps"}:
        return value / 1000.0
    if u in {"gpm", "us gpm"}:
        return gpm_to_m3s(value)
    raise ValueError(f"Unsupported pump-curve flow unit: {unit}")


def _head_to_m(value: float, unit: str) -> float:
    u = unit.strip().lower()
    if u in {"m", "meter", "metre"}:
        return value
    if u in {"ft", "feet", "foot"}:
        return ft_to_m(value)
    raise ValueError(f"Unsupported pump-curve head unit: {unit}")


def _npsh_to_m(value: float, unit: str) -> float:
    return _head_to_m(value, unit)


def _normalize_manufacturer(manufacturer: dict[str, Any]) -> dict[str, Any]:
    flow_unit = manufacturer.get("flow_unit", "m³/s")
    head_unit = manufacturer.get("head_unit", "m")
    npshr_unit = manufacturer.get("npshr_unit", head_unit)
    normalized = dict(manufacturer)
    normalized["curve_points"] = []
    for raw in manufacturer.get("curve_points", []):
        point = dict(raw)
        point["flow"] = _flow_to_si(float(raw["flow"]), flow_unit)
        point["head"] = _head_to_m(float(raw["head"]), head_unit)
        if raw.get("npshr") is not None:
            point["npshr"] = _npsh_to_m(float(raw["npshr"]), npshr_unit)
        normalized["curve_points"].append(point)
    if manufacturer.get("motor_power") is not None:
        unit = str(manufacturer.get("motor_power_unit", "kW")).lower()
        if unit == "kw":
            normalized["motor_power_kw"] = float(manufacturer["motor_power"])
        elif unit in {"hp", "hp(mechanical)"}:
            normalized["motor_power_kw"] = float(manufacturer["motor_power"]) * 0.745699872
        else:
            raise ValueError(f"Unsupported motor power unit: {manufacturer.get('motor_power_unit')}")
    return normalized


def validate_commercial_pump(
    duty: dict[str, Any],
    manufacturer: dict[str, Any],
    *,
    system_curve: list[tuple[float, float]] | None = None,
) -> dict[str, Any]:
    """Validate one manufacturer pump curve against a deterministic duty point.

    No manufacturer data is inferred. If optional efficiency/NPSHr data are
    absent, those checks are reported as NOT_CHECKED.
    """
    flow = duty.get("flow")
    head = duty.get("head")
    if flow is None or head is None:
        return {"status": "NOT_CALCULABLE", "selection_status": "COMMERCIAL_PUMP_NOT_SELECTED", "issues": ["Deterministic design flow and head are required before commercial pump validation."]}

    manufacturer = _normalize_manufacturer(manufacturer)
    points = validate_curve_points(manufacturer.get("curve_points", []))
    pump_head = _interp(points, float(flow), "head")
    if pump_head is None:
        return {
            "status": "FAIL",
            "selection_status": "COMMERCIAL_PUMP_NOT_SELECTED",
            "manufacturer": manufacturer.get("manufacturer"),
            "model": manufacturer.get("model"),
            "duty_point": {"flow": flow, "head": head},
            "issues": ["Duty flow is outside the supplied manufacturer pump-curve range."],
        }

    head_margin = pump_head - float(head)
    issues: list[str] = []
    checks: list[dict[str, Any]] = []
    checks.append({"name": "Duty head compatibility", "status": "PASS" if head_margin >= 0 else "FAIL", "pump_head": pump_head, "required_head": head, "head_margin": head_margin})

    efficiency = _interp(points, float(flow), "efficiency")
    if efficiency is None:
        checks.append({"name": "Efficiency", "status": "NOT_CHECKED", "message": "Manufacturer efficiency data are not available at the duty flow."})
    else:
        checks.append({"name": "Efficiency", "status": "AVAILABLE", "value": efficiency})

    shaft_power_kw = None
    if efficiency is not None and float(efficiency) > 0:
        hydraulic_kw = duty.get("hydraulic_power")
        if hydraulic_kw is not None:
            shaft_power_kw = float(hydraulic_kw) / float(efficiency)
        checks.append({"name": "Pump shaft/input power", "status": "CALCULATED", "value_kw": shaft_power_kw})
        motor_kw = manufacturer.get("motor_power_kw")
        if motor_kw is not None and shaft_power_kw is not None:
            checks.append({"name": "Motor power", "status": "PASS" if motor_kw >= shaft_power_kw else "FAIL", "manufacturer_motor_power_kw": motor_kw, "calculated_pump_input_power_kw": shaft_power_kw})
        else:
            checks.append({"name": "Motor power", "status": "NOT_CHECKED", "message": "Manufacturer motor rating was not supplied."})

    npshr = _interp(points, float(flow), "npshr")
    npsha = duty.get("npsha")
    if npshr is None:
        checks.append({"name": "NPSH", "status": "NOT_CHECKED", "message": "Manufacturer NPSHr data are not available at the duty flow."})
    elif npsha is None:
        checks.append({"name": "NPSH", "status": "NOT_CHECKED", "npshr": npshr, "message": "NPSHa is not available from the deterministic design result."})
    else:
        npsh_margin = float(npsha) - npshr
        checks.append({"name": "NPSH", "status": "PASS" if npsh_margin >= 0 else "FAIL", "npsha": npsha, "npshr": npshr, "margin": npsh_margin})

    if head_margin < 0:
        issues.append("Manufacturer pump curve does not provide the required head at the design flow.")
    if any(c["status"] == "FAIL" for c in checks):
        status = "FAIL"
    else:
        status = "PASS"

    operating_point = None
    if system_curve is not None:
        operating_point = _system_intersection(points, system_curve)
        if operating_point is None:
            issues.append("No pump/system-curve intersection could be established from the supplied curve ranges.")

    return {
        "status": status,
        "selection_status": "COMMERCIAL_PUMP_CANDIDATE_VALIDATED" if status == "PASS" else "COMMERCIAL_PUMP_NOT_SELECTED",
        "manufacturer": manufacturer.get("manufacturer"),
        "model": manufacturer.get("model"),
        "curve_source": manufacturer.get("curve_source"),
        "duty_point": {"flow": flow, "head": head},
        "interpolated_pump_performance": {"head": pump_head, "efficiency": efficiency, "npshr": npshr},
        "head_margin": head_margin,
        "checks": checks,
        "operating_point": operating_point,
        "issues": issues,
        "important_note": "This validates compatibility of the supplied manufacturer data; it does not rank pumps or claim a best/optimal selection.",
    }
