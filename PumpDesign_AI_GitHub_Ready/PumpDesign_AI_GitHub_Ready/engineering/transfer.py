
"""Transfer pump engineering workflow.

Connects frozen transfer-pump inputs to deterministic calculations.
The workflow does not invent missing engineering inputs.
"""

from __future__ import annotations

from engineering.duty import attach_pump_duty

from typing import Any

from calculations.demand import transfer_flow, demand_from_population
from calculations.hydraulics import static_head, hydraulic_power
from calculations.pipe_sizing import size_pipe_candidates, select_first_acceptable
from calculations.units import gpm_to_m3s, ft_to_m, mm_to_m


def _value(obj: Any, name: str):
    if isinstance(obj, dict):
        return obj.get(name)
    return getattr(obj, name, None)


def _missing(*values):
    return any(v is None for v in values)


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


def run_transfer_design(data: dict, *, rag_context: dict | None = None) -> dict:
    """Run the transfer-pump design workflow.

    Expected frozen fields are accepted in a unit-aware form. Each numeric field
    may be either a raw number plus a sibling ``*_unit`` field, or
    ``{"value": ..., "unit": ...}``.
    """
    refs = (rag_context or {}).get("references", [])
    criteria = (rag_context or {}).get("velocity_criteria")
    hw_c = (rag_context or {}).get("hazen_williams_c")

    out = {
        "application": "TRANSFER_PUMP",
        "status": "CALCULATED",
        "calculations": [],
        "pipe_sizing": {},
        "validation": [],
    }

    # Demand / design flow
    demand_method = _value(data, "demand_method")
    total_demand = _value(data, "total_design_demand")
    population = _value(data, "population")
    per_capita = _value(data, "per_capita_demand")
    transfer_time = _value(data, "required_transfer_time")
    oht_capacity = _value(data, "oht_capacity")

    if demand_method == "POPULATION" and not _missing(population, per_capita):
        pop_value = population["value"] if isinstance(population, dict) else population
        pc_value = per_capita["value"] if isinstance(per_capita, dict) else per_capita
        d = demand_from_population(pop_value, pc_value)
        out["calculations"].append(_result(
            "Daily demand", "CALCULATED", d.flow, d.unit,
            d.formula, d.inputs, d.method,
            references=refs
        ))

    # Full-fill transfer basis: OHT capacity.
    if oht_capacity is None or transfer_time is None:
        out["calculations"].append(_result(
            "Transfer design flow", "MISSING_INPUT",
            formula="Q = V / t",
            message="OHT capacity and required transfer time are required for the full-fill transfer basis."
        ))
        out["status"] = "MISSING_INPUT"
        return attach_pump_duty(out)

    volume_gal = oht_capacity["value"] if isinstance(oht_capacity, dict) else oht_capacity
    time_min = transfer_time["value"] if isinstance(transfer_time, dict) else transfer_time
    q = transfer_flow(volume_gal, time_min)
    out["calculations"].append(_result(
        "Transfer design flow", "CALCULATED", q.flow, q.unit,
        q.formula, q.inputs, q.method,
        assumptions=["Transfer volume is based on the finalized full-fill OHT capacity basis."],
        references=refs
    ))

    # Static head from finalized tank water levels.
    ugt_level = _value(data, "ugt_design_water_level")
    oht_level = _value(data, "oht_design_water_level")
    if _missing(ugt_level, oht_level):
        out["calculations"].append(_result(
            "Static head", "MISSING_INPUT",
            formula="Hs = Z2 - Z1",
            message="UGT and OHT design water levels are required."
        ))
        out["status"] = "MISSING_INPUT"
    else:
        z1 = ugt_level["value"] if isinstance(ugt_level, dict) else ugt_level
        z2 = oht_level["value"] if isinstance(oht_level, dict) else oht_level
        if isinstance(ugt_level, dict) and ugt_level.get("unit") == "ft":
            z1 = ft_to_m(z1)
        if isinstance(oht_level, dict) and oht_level.get("unit") == "ft":
            z2 = ft_to_m(z2)
        sh = static_head(z1, z2)
        out["calculations"].append(_result(
            "Static head", "CALCULATED", sh.value, sh.unit,
            sh.formula, sh.inputs, sh.method,
            references=refs
        ))

    # Pipe sizing: suction and delivery use their respective finalized lengths.
    material = _value(data, "pipe_material")
    if material == "MS":
        material = "MS/carbon steel"
    suction_length = _value(data, "suction_pipe_length")
    delivery_length = _value(data, "delivery_pipe_length")
    if material is None:
        out["pipe_sizing"]["status"] = "MISSING_INPUT"
        out["pipe_sizing"]["message"] = "Pipe material is required."
        out["status"] = "MISSING_INPUT"
    else:
        for name, length in (("suction", suction_length), ("delivery", delivery_length)):
            if length is None:
                out["pipe_sizing"][name] = {
                    "status": "MISSING_INPUT",
                    "message": f"{name.title()} pipe length is required."
                }
                out["status"] = "MISSING_INPUT"
                continue
            flow_m3s = gpm_to_m3s(q.flow)
            length_value = length["value"] if isinstance(length, dict) else length
            if isinstance(length, dict) and length.get("unit") == "ft":
                length_value = ft_to_m(length_value)
            min_v = criteria.get("min_mps") if isinstance(criteria, dict) else None
            max_v = criteria.get("max_mps") if isinstance(criteria, dict) else None
            candidates = size_pipe_candidates(
                flow_m3s=flow_m3s,
                material=material,
                velocity_min_mps=min_v,
                velocity_max_mps=max_v,
                hazen_williams_c=hw_c,
                length_m=length_value,
            )
            selected = select_first_acceptable(candidates)
            out["pipe_sizing"][name] = {
                "status": "CALCULATED",
                "candidate_count": len(candidates),
                "selected": {
                    "size": selected.pipe.size_label,
                    "standard": selected.pipe.standard,
                    "schedule_or_sdr": selected.pipe.schedule_or_sdr,
                    "inside_diameter_m": selected.pipe.inside_diameter_m,
                    "velocity_mps": selected.velocity_mps,
                    "head_loss_m": selected.head_loss_m,
                } if selected else None,
                "selection_status": "SELECTED" if selected else "NOT_SELECTED",
                "selection_message": (
                    "Smallest candidate satisfying the supplied velocity criterion."
                    if selected else
                    "No pipe selected because no applicable velocity criterion was supplied or no candidate passed it."
                ),
                "candidates": [
                    {
                        "size": c.pipe.size_label,
                        "standard": c.pipe.standard,
                        "schedule_or_sdr": c.pipe.schedule_or_sdr,
                        "inside_diameter_m": c.pipe.inside_diameter_m,
                        "velocity_mps": c.velocity_mps,
                        "head_loss_m": c.head_loss_m,
                        "velocity_status": c.velocity_status,
                        "hydraulic_status": c.hydraulic_status,
                        "applicable": c.applicable,
                    } for c in candidates
                ],
            }

    # TDH can be completed only from the available loss terms. Minor losses
    # are deliberately not invented because fittings/valves were not finalized inputs.
    if all(c.get("status") == "CALCULATED" for c in out["calculations"] if c["name"] in ("Static head", "Transfer design flow")):
        sh = next(c["value"] for c in out["calculations"] if c["name"] == "Static head")
        total_loss = 0.0
        loss_parts = []
        for side in ("suction", "delivery"):
            ps = out["pipe_sizing"].get(side, {})
            selected = ps.get("selected")
            if selected and selected.get("head_loss_m") is not None:
                total_loss += selected["head_loss_m"]
                loss_parts.append((side, selected["head_loss_m"]))
        tdh = sh + total_loss
        out["calculations"].append(_result(
            "Total Dynamic Head", "CALCULATED", tdh, "m",
            formula="H_pump = H_static + h_major + h_minor",
            inputs={"static_head_m": sh, "major_losses_m": total_loss, "minor_losses_m": None},
            method="Energy equation; available major-loss terms only",
            assumptions=["Minor losses are not fabricated because fittings/valves were not finalized inputs."],
            references=refs,
            message="TDH is provisional until applicable minor losses are supplied or otherwise deterministically derived."
        ))
        out["validation"].append({
            "name": "TDH completeness",
            "status": "WARNING",
            "severity": "WARNING",
            "message": "Minor losses are not included because no fitting/valve inputs are available."
        })

        hp = hydraulic_power(gpm_to_m3s(q.flow), tdh)
        out["calculations"].append(_result(
            "Hydraulic power", "CALCULATED", hp.value, hp.unit,
            hp.formula, hp.inputs, hp.method, references=refs
        ))

    out["design_basis"] = {
        "demand_method": demand_method,
        "total_design_demand_supplied": total_demand is not None,
        "population_supplied": population is not None,
        "per_capita_supplied": per_capita is not None,
        "transfer_volume_basis": "OHT capacity",
    }
    return attach_pump_duty(out)
