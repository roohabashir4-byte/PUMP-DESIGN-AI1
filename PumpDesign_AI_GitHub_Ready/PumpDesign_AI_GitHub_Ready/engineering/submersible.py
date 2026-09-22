
"""Submersible pump engineering workflow.

Frozen input basis:
- Tube Well/Borehole -> UGT
- Tube Well/Borehole -> OHT
- Sump -> UGT
- Sump -> OHT
- Different Scenario -> handled by the agent before routing here.

The deterministic layer owns numerical calculations. It does not invent
well yield, flow, source levels, pipe criteria, minor losses, NPSHR, or
manufacturer pump data.
"""

from __future__ import annotations

from engineering.duty import attach_pump_duty
from typing import Any

from calculations.hydraulics import static_head, hydraulic_power
from calculations.pipe_sizing import size_pipe_candidates, select_first_acceptable
from calculations.units import gpm_to_m3s, ft_to_m


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
        "name": name,
        "status": status,
        "value": value,
        "unit": unit,
        "formula": formula,
        "inputs": inputs or {},
        "method": method,
        "assumptions": assumptions or [],
        "references": references or [],
        "message": message,
    }


def _level_to_m(x):
    value = _num(x)
    unit = _unit(x)
    if value is None:
        return None
    if unit == "ft":
        return ft_to_m(value)
    if unit == "m":
        return value
    raise ValueError(f"Unsupported water-level unit: {unit}")


def _length_to_m(x):
    value = _num(x)
    unit = _unit(x)
    if value is None:
        return None
    if unit == "ft":
        return ft_to_m(value)
    if unit == "m":
        return value
    raise ValueError(f"Unsupported pipe-length unit: {unit}")


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
    return None


def _flow_from_filling(volume, filling_time):
    v = _num(volume)
    t = _num(filling_time)
    vu = _unit(volume)
    tu = _unit(filling_time)

    if v is None or t is None:
        return None

    if vu in ("US gal", "gal"):
        volume_m3 = v * 0.003785411784
    elif vu in ("m3", "m³"):
        volume_m3 = v
    elif vu in ("L", "l"):
        volume_m3 = v / 1000.0
    else:
        raise ValueError(f"Unsupported filling-volume unit: {vu}")

    if tu in ("min", "minute", "minutes"):
        time_s = t * 60.0
    elif tu in ("h", "hr", "hour", "hours"):
        time_s = t * 3600.0
    elif tu in ("s", "sec", "second", "seconds"):
        time_s = t
    else:
        raise ValueError(f"Unsupported filling-time unit: {tu}")

    if volume_m3 <= 0 or time_s <= 0:
        raise ValueError("Filling volume and filling time must be greater than zero.")

    q_m3s = volume_m3 / time_s
    return {
        "flow_m3s": q_m3s,
        "formula": "Q = V/t",
        "inputs": {"volume_m3": volume_m3, "time_s": time_s},
        "method": "Destination filling volume / required filling time",
    }


def _source_type(data):
    scenario = _value(data, "primary_use")
    if scenario and scenario.startswith("TUBE_WELL"):
        return "TUBE_WELL"
    if scenario and scenario.startswith("SUMP"):
        return "SUMP"
    return None


def run_submersible_design(data: dict, *, rag_context: dict | None = None) -> dict:
    rag = rag_context or {}
    refs = rag.get("references", [])
    criteria = rag.get("velocity_criteria")
    hw_c = rag.get("hazen_williams_c")

    out = {
        "application": "SUBMERSIBLE_PUMP",
        "status": "CALCULATED",
        "calculations": [],
        "pipe_sizing": {},
        "validation": [],
    }

    scenario = _value(data, "primary_use")
    source_type = _source_type(data)

    if source_type is None:
        out["status"] = "MISSING_INPUT"
        out["calculations"].append(_result(
            "Source type", "MISSING_INPUT",
            message="Select a supported tube-well/borehole or sump scenario."
        ))
        return attach_pump_duty(out)

    # 1. Design flow: known design flow or explicitly required filling time.
    known_flow = _value(data, "known_design_flow")
    filling_time = _value(data, "required_filling_time")

    if known_flow is not None:
        q_m3s = _flow_to_m3s(known_flow)
        flow_basis = "USER_SUPPLIED_DESIGN_FLOW"
        flow_inputs = {"design_flow": known_flow}
        flow_formula = "Qdesign = supplied design flow"
        flow_method = "User-supplied design flow"
    else:
        destination_capacity = _value(data, "destination_capacity")
        if destination_capacity is None or filling_time is None:
            out["status"] = "MISSING_INPUT"
            out["calculations"].append(_result(
                "Submersible design flow", "MISSING_INPUT",
                formula="Q = V/t",
                message="Provide a known design flow, or provide destination filling volume and required filling time."
            ))
            return attach_pump_duty(out)
        flow = _flow_from_filling(destination_capacity, filling_time)
        q_m3s = flow["flow_m3s"]
        flow_basis = "FILLING_TIME"
        flow_inputs = flow["inputs"]
        flow_formula = flow["formula"]
        flow_method = flow["method"]

    if q_m3s is None or q_m3s <= 0:
        raise ValueError("A positive submersible design flow is required.")

    out["calculations"].append(_result(
        "Submersible design flow", "CALCULATED", q_m3s, "m³/s",
        flow_formula, flow_inputs, flow_method, references=refs
    ))

    # 2. Source capacity / water-level basis.
    if source_type == "TUBE_WELL":
        dynamic = _value(data, "dynamic_water_level")
        well_yield = _value(data, "well_yield")

        if dynamic is None:
            out["status"] = "MISSING_INPUT"
            out["calculations"].append(_result(
                "Dynamic water level", "MISSING_INPUT",
                message="Dynamic water level is required for a pumping tube-well design."
            ))
            return attach_pump_duty(out)

        source_level = _level_to_m(dynamic)
        source_basis = "Dynamic water level during pumping"

        out["calculations"].append(_result(
            "Source water level", "CALCULATED", source_level, "m",
            formula="Zsource = dynamic water level",
            inputs={"dynamic_water_level": dynamic},
            method=source_basis,
            references=refs
        ))

        if well_yield is not None:
            yield_m3s = _flow_to_m3s(well_yield)
            if yield_m3s is not None:
                yield_status = "PASS" if q_m3s <= yield_m3s else "FAIL"
                out["calculations"].append(_result(
                    "Well yield check", "CALCULATED",
                    yield_m3s, "m³/s",
                    formula="Qpump ≤ Qwell",
                    inputs={"pump_design_flow_m3s": q_m3s, "well_yield_m3s": yield_m3s},
                    method="Source-capacity check",
                    references=refs,
                    message=(
                        "Design flow does not exceed the supplied sustainable well yield."
                        if yield_status == "PASS"
                        else
                        "Design flow exceeds the supplied well yield; source capacity is inadequate for this design basis."
                    )
                ))
                out["validation"].append({
                    "name": "Well yield capacity",
                    "status": yield_status,
                    "severity": "INFO" if yield_status == "PASS" else "CRITICAL",
                    "message": "Qpump ≤ Qwell" if yield_status == "PASS" else "Qpump > Qwell",
                })
            else:
                out["calculations"].append(_result(
                    "Well yield check", "NOT_CALCULABLE",
                    formula="Qpump ≤ Qwell",
                    message="Well-yield unit is not an instantaneous flow unit supported by the deterministic engine."
                ))
        else:
            out["validation"].append({
                "name": "Well yield capacity",
                "status": "WARNING",
                "severity": "WARNING",
                "message": "Well yield was not supplied; source-capacity validation is pending. No yield was assumed."
            })

    else:
        sump_level = _value(data, "sump_water_level")
        if sump_level is None:
            out["status"] = "MISSING_INPUT"
            out["calculations"].append(_result(
                "Source water level", "MISSING_INPUT",
                message="Sump water level is required."
            ))
            return attach_pump_duty(out)
        source_level = _level_to_m(sump_level)
        out["calculations"].append(_result(
            "Source water level", "CALCULATED", source_level, "m",
            formula="Zsource = sump water level",
            inputs={"sump_water_level": sump_level},
            method="Sump operating water level",
            references=refs
        ))

    # 3. Destination level.
    destination = _value(data, "destination_water_level")
    if destination is None:
        out["status"] = "MISSING_INPUT"
        out["calculations"].append(_result(
            "Destination water level", "MISSING_INPUT",
            message="Destination water level is required."
        ))
        return attach_pump_duty(out)

    destination_level = _level_to_m(destination)
    sh = static_head(source_level, destination_level)
    out["calculations"].append(_result(
        "Static elevation head", "CALCULATED", sh.value, sh.unit,
        sh.formula, sh.inputs, sh.method, references=refs
    ))

    if sh.value < 0:
        out["validation"].append({
            "name": "Static elevation direction",
            "status": "WARNING",
            "severity": "WARNING",
            "message": "Destination water level is below source water level. Verify the selected submersible scenario and hydraulic boundary conditions."
        })

    # 4. Delivery pipe sizing.
    material = _value(data, "pipe_material")
    length = _value(data, "delivery_pipe_length")
    if material is None or length is None:
        out["status"] = "MISSING_INPUT"
        out["pipe_sizing"] = {
            "status": "MISSING_INPUT",
            "message": "Delivery pipe length and pipe material are required."
        }
        return attach_pump_duty(out)

    length_m = _length_to_m(length)
    min_v = criteria.get("min_mps") if isinstance(criteria, dict) else None
    max_v = criteria.get("max_mps") if isinstance(criteria, dict) else None

    candidates = size_pipe_candidates(
        flow_m3s=q_m3s,
        material=material,
        velocity_min_mps=min_v,
        velocity_max_mps=max_v,
        hazen_williams_c=hw_c,
        length_m=length_m,
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
            "No automatic pipe selection because an applicable velocity criterion was not supplied or no candidate passed it."
        ),
    }

    # 5. TDH and power.
    if selected is None or selected.head_loss_m is None:
        out["status"] = "NOT_CALCULABLE"
        out["calculations"].append(_result(
            "Total Dynamic Head", "NOT_CALCULABLE",
            formula="Hpump = Hstatic + hmajor + hminor",
            inputs={"static_head_m": sh.value,
                    "major_loss_m": selected.head_loss_m if selected else None,
                    "minor_loss_m": None},
            message="Final pump head cannot be completed until a pipe-loss value is available."
        ))
    else:
        tdh = sh.value + selected.head_loss_m
        out["calculations"].append(_result(
            "Total Dynamic Head", "CALCULATED", tdh, "m",
            formula="Hpump = Hstatic + hmajor + hminor",
            inputs={"static_head_m": sh.value,
                    "major_loss_m": selected.head_loss_m,
                    "minor_loss_m": None},
            method="Energy equation; available major-loss term only",
            assumptions=["Minor losses are not fabricated because fittings/valves are not frozen inputs."],
            references=refs,
            message="TDH is provisional until applicable minor losses are included."
        ))
        out["validation"].append({
            "name": "TDH completeness",
            "status": "WARNING",
            "severity": "WARNING",
            "message": "Minor losses are not included because fittings/valves are not finalized inputs."
        })

        hp = hydraulic_power(q_m3s, tdh)
        out["calculations"].append(_result(
            "Hydraulic power", "CALCULATED", hp.value, hp.unit,
            hp.formula, hp.inputs, hp.method, references=refs
        ))

    # NPSH: do not invent a pump setting depth or manufacturer NPSHR.
    out["calculations"].append(_result(
        "NPSH review", "NOT_CALCULABLE",
        formula="NPSHa is system-derived; NPSHr is manufacturer-pump data",
        message=(
            "NPSHa is not calculated in this workflow because pump setting depth/suction "
            "boundary data are not frozen inputs. NPSHr must come from the selected pump manufacturer."
        ),
        references=refs
    ))

    out["design_basis"] = {
        "scenario": scenario,
        "source_type": source_type,
        "flow_basis": flow_basis,
        "source_level_basis": "Dynamic water level" if source_type == "TUBE_WELL" else "Sump water level",
        "well_yield_is_capacity_check": source_type == "TUBE_WELL",
    }
    return attach_pump_duty(out)
