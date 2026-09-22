
"""Booster pump engineering workflow.

Uses the frozen Booster Pump inputs. Numerical calculations are deterministic;
criteria and design-flow methodology may be supplied by RAG/agent context.
"""

from __future__ import annotations

from engineering.duty import attach_pump_duty
from typing import Any

from calculations.hydraulics import static_head, pressure_head, hydraulic_power
from calculations.pipe_sizing import size_pipe_candidates, select_first_acceptable
from calculations.units import gpm_to_m3s, ft_to_m, psi_to_pa


def _value(obj: Any, name: str):
    if isinstance(obj, dict):
        return obj.get(name)
    return getattr(obj, name, None)


def _num(obj):
    if isinstance(obj, dict):
        return obj.get("value")
    return obj


def _unit(obj):
    return obj.get("unit") if isinstance(obj, dict) else None


def _result(name, status, value=None, unit=None, formula=None, inputs=None,
            method=None, assumptions=None, references=None, message=None):
    return {
        "name": name, "status": status, "value": value, "unit": unit,
        "formula": formula, "inputs": inputs or {}, "method": method,
        "assumptions": assumptions or [], "references": references or [],
        "message": message,
    }


def _pressure_head_from_input(pressure, density=998.0):
    value = _num(pressure)
    unit = _unit(pressure)
    if value is None:
        return None
    if unit in ("psi", "PSI"):
        return pressure_head(psi_to_pa(value), density)
    if unit in ("Pa", "pa"):
        return pressure_head(value, density)
    if unit in ("kPa", "kpa"):
        return pressure_head(value * 1000.0, density)
    if unit in ("bar", "Bar"):
        return pressure_head(value * 100000.0, density)
    if unit in ("m", "mH2O", "mWC"):
        from calculations.hydraulics import HydraulicResult
        return HydraulicResult(value, "m", "H = ΔP/(ρg)", {"pressure_head": value}, "Supplied pressure head")
    if unit in ("ft", "ftH2O", "ftWC"):
        from calculations.hydraulics import HydraulicResult
        return HydraulicResult(ft_to_m(value), "m", "H = ΔP/(ρg)", {"pressure_head_ft": value}, "Supplied pressure head")
    raise ValueError(f"Unsupported pressure unit: {unit}")


def _elevation_to_m(x):
    value = _num(x)
    unit = _unit(x)
    if value is None:
        return None
    if unit == "ft":
        return ft_to_m(value)
    if unit == "m":
        return value
    raise ValueError(f"Unsupported elevation unit: {unit}")


def _flow_to_m3s(x):
    value = _num(x)
    unit = _unit(x)
    if value is None:
        return None
    if unit in ("gpm", "US gal/min"):
        return gpm_to_m3s(value)
    if unit in ("m3/s", "m³/s"):
        return value
    if unit in ("L/s", "l/s"):
        return value / 1000.0
    # Daily-demand units are not instantaneous pump flow.
    if unit in ("gpd", "US gal/day", "m3/day", "m³/day", "L/day"):
        return None
    raise ValueError(f"Unsupported design-flow unit: {unit}")


def _flow_from_rag(data, rag):
    """Use an explicitly supplied design-flow criterion, never an arbitrary factor."""
    total = _value(data, "total_design_demand")
    if total is not None:
        f = _flow_to_m3s(total)
        if f is not None:
            return f, "USER_SUPPLIED_DESIGN_FLOW"

    # RAG may define an explicit conversion from a daily demand basis.
    pop = _value(data, "population")
    pc = _value(data, "per_capita_demand")
    method = (rag or {}).get("design_flow_method")
    if method and method.get("peak_factor") is not None and pop is not None and pc is not None:
        daily_gpd = _num(pop) * _num(pc)
        peak_factor = float(method["peak_factor"])
        # US gal/day -> m3/s
        q = daily_gpd * 0.003785411784 / 86400.0 * peak_factor
        return q, "RAG_SUPPLIED_DEMAND_METHOD"

    return None, None


def run_booster_design(data: dict, *, rag_context: dict | None = None) -> dict:
    rag = rag_context or {}
    refs = rag.get("references", [])
    criteria = rag.get("velocity_criteria")
    hw_c = rag.get("hazen_williams_c")

    out = {
        "application": "BOOSTER_PUMP",
        "status": "CALCULATED",
        "calculations": [],
        "pipe_sizing": {},
        "validation": [],
    }

    # 1. Design flow
    q_m3s, flow_basis = _flow_from_rag(data, rag)
    if q_m3s is None:
        out["calculations"].append(_result(
            "Booster design flow", "MISSING_INPUT",
            formula="Qdesign = project design flow or RAG-defined demand methodology",
            message="A booster design flow is required. A daily demand cannot be silently treated as instantaneous pump flow."
        ))
        out["status"] = "MISSING_INPUT"
        return attach_pump_duty(out)

    out["calculations"].append(_result(
        "Booster design flow", "CALCULATED", q_m3s, "m³/s",
        formula="Qdesign = supplied/project design flow or explicitly referenced demand method",
        inputs={"flow_basis": flow_basis},
        method=flow_basis,
        references=refs
    ))

    # 2. Elevation head
    # The frozen booster basis identifies the OHT/source water level as the
    # hydraulic source and the highest served elevation as the critical
    # elevation for required pump head. The lowest served elevation is retained
    # for a later overpressure/zone check; it must not replace the source level.
    source_level = _value(data, "oht_design_water_level")
    high = _value(data, "highest_elevation_served")
    low = _value(data, "lowest_elevation_served")

    if source_level is None or high is None:
        out["calculations"].append(_result(
            "Elevation head", "MISSING_INPUT",
            formula="He = Zhighest served - ZOHT/source",
            message="OHT/source design water level and highest served elevation are required."
        ))
        out["status"] = "MISSING_INPUT"
    else:
        he = static_head(_elevation_to_m(source_level), _elevation_to_m(high))
        out["calculations"].append(_result(
            "Elevation head", "CALCULATED", he.value, he.unit,
            "He = Zhighest served - ZOHT/source",
            {"Zsource": _elevation_to_m(source_level),
             "Zhighest": _elevation_to_m(high)},
            he.method,
            references=refs
        ))

        if low is not None and _elevation_to_m(low) > _elevation_to_m(high):
            out["validation"].append({
                "name": "Served-zone elevations",
                "status": "FAIL",
                "severity": "CRITICAL",
                "message": "Lowest served elevation cannot be above the highest served elevation."
            })

    # 3. Required residual pressure
    residual = _value(data, "required_residual_pressure")
    if residual is None:
        out["calculations"].append(_result(
            "Required residual-pressure head", "MISSING_INPUT",
            formula="Hres = ΔP/(ρg)",
            message="Required residual pressure is required."
        ))
        out["status"] = "MISSING_INPUT"
    else:
        hp = _pressure_head_from_input(residual)
        out["calculations"].append(_result(
            "Required residual-pressure head", "CALCULATED", hp.value, hp.unit,
            hp.formula, hp.inputs, hp.method, references=refs
        ))

    # 4. Available inlet pressure
    available = _value(data, "available_inlet_pressure")
    if available is not None:
        ha = _pressure_head_from_input(available)
        out["calculations"].append(_result(
            "Available inlet-pressure head", "CALCULATED", ha.value, ha.unit,
            ha.formula, ha.inputs, ha.method, references=refs
        ))

    # 5. Critical route pipe sizing
    material = _value(data, "pipe_material")
    route = _value(data, "critical_route_length")
    if material is None or route is None:
        out["pipe_sizing"]["status"] = "MISSING_INPUT"
        out["pipe_sizing"]["message"] = "Critical route length and pipe material are required."
        out["status"] = "MISSING_INPUT"
    else:
        flow_m3s = q_m3s
        route_m = _elevation_to_m(route)
        min_v = criteria.get("min_mps") if isinstance(criteria, dict) else None
        max_v = criteria.get("max_mps") if isinstance(criteria, dict) else None
        candidates = size_pipe_candidates(
            flow_m3s=flow_m3s, material=material,
            velocity_min_mps=min_v, velocity_max_mps=max_v,
            hazen_williams_c=hw_c, length_m=route_m
        )
        selected = select_first_acceptable(candidates)
        out["pipe_sizing"] = {
            "status": "CALCULATED",
            "candidate_count": len(candidates),
            "selection_status": "SELECTED" if selected else "NOT_SELECTED",
            "selected": {
                "size": selected.pipe.size_label,
                "standard": selected.pipe.standard,
                "schedule_or_sdr": selected.pipe.schedule_or_sdr,
                "inside_diameter_m": selected.pipe.inside_diameter_m,
                "velocity_mps": selected.velocity_mps,
                "head_loss_m": selected.head_loss_m,
            } if selected else None,
            "selection_message": (
                "Smallest candidate satisfying the supplied velocity criterion."
                if selected else
                "No automatic pipe selection: an applicable velocity criterion was not supplied or no candidate passed it."
            ),
        }

    # 6. Required booster head
    calc = {c["name"]: c for c in out["calculations"]}
    if "Elevation head" in calc and calc["Elevation head"]["status"] == "CALCULATED" \
       and "Required residual-pressure head" in calc and calc["Required residual-pressure head"]["status"] == "CALCULATED":
        elevation = calc["Elevation head"]["value"]
        residual_h = calc["Required residual-pressure head"]["value"]
        available_h = calc.get("Available inlet-pressure head", {}).get("value", 0.0)

        selected = out["pipe_sizing"].get("selected")
        major = selected.get("head_loss_m") if selected else None
        if major is None:
            out["calculations"].append(_result(
                "Required booster head", "NOT_CALCULABLE",
                formula="Hbooster = He + Hres + Hloss - Havailable",
                inputs={"elevation_head_m": elevation, "residual_head_m": residual_h,
                        "major_loss_m": major, "available_head_m": available_h},
                message="A pipe-loss value is required before final booster head can be calculated."
            ))
            out["status"] = "NOT_CALCULABLE"
        else:
            head = elevation + residual_h + major - available_h
            if head < 0:
                head = 0.0
            out["calculations"].append(_result(
                "Required booster head", "CALCULATED", head, "m",
                formula="Hbooster = He + Hres + Hmajor + Hminor - Havailable",
                inputs={"elevation_head_m": elevation, "residual_head_m": residual_h,
                        "major_loss_m": major, "minor_loss_m": None,
                        "available_head_m": available_h},
                method="Energy balance; available major losses only",
                assumptions=["Minor losses are not fabricated because they are not finalized UI inputs."],
                references=refs,
                message="Booster head is provisional until applicable minor losses are included."
            ))
            out["validation"].append({
                "name": "Booster-head completeness",
                "status": "WARNING",
                "severity": "WARNING",
                "message": "Minor losses are not included because fittings/valves are not finalized inputs."
            })
            hp = hydraulic_power(q_m3s, head)
            out["calculations"].append(_result(
                "Hydraulic power", "CALCULATED", hp.value, hp.unit,
                hp.formula, hp.inputs, hp.method, references=refs
            ))

    out["design_basis"] = {
        "flow_basis": flow_basis,
        "pressure_zone": "Frozen Booster Pump scenario",
    }
    return attach_pump_duty(out)
