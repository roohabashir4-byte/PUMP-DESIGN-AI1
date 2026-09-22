
"""Hot-water recirculation pump engineering workflow.

Frozen UI basis:
- Central heater + vertical riser
- Central heater + horizontal floor loops
- Combined vertical + horizontal distribution
- Separate hot-water zones
- Different Scenario -> interpreted by the agent before routing here

The recirculation flow is heat-loss based, not domestic hot-water demand based.
Heat-loss criteria/properties come from RAG context. No universal heat-loss
rate is hard-coded.
"""

from __future__ import annotations

from engineering.duty import attach_pump_duty
from typing import Any

from calculations.hydraulics import hazen_williams_head_loss, hydraulic_power, velocity
from calculations.pipe_sizing import size_pipe_candidates, select_first_acceptable


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


def _temperature_to_c(x):
    value=_num(x)
    unit=_unit(x)
    if value is None:
        return None
    if unit in ("C","°C"):
        return value
    if unit in ("F","°F"):
        return (value-32.0)*5.0/9.0
    raise ValueError(f"Unsupported temperature unit: {unit}")


def _length_to_m(x):
    value=_num(x)
    unit=_unit(x)
    if value is None:
        return None
    if unit=="m":
        return value
    if unit=="ft":
        return value*0.3048
    raise ValueError(f"Unsupported length unit: {unit}")


def _density_kg_m3(rag, temperature_c):
    # RAG may provide a temperature-dependent property table/function result.
    props=rag.get("water_properties", {})
    if isinstance(props, dict):
        rho=props.get("density_kg_m3")
        if rho is not None:
            return float(rho)
    return None


def _cp_j_kgk(rag):
    props=rag.get("water_properties", {})
    if isinstance(props, dict):
        cp=props.get("cp_j_kgk")
        if cp is not None:
            return float(cp)
    return None


def run_hot_water_recirc_design(data: dict, *, rag_context: dict | None = None) -> dict:
    rag=rag_context or {}
    refs=rag.get("references", [])
    out={
        "application":"HOT_WATER_RECIRCULATION_PUMP",
        "status":"CALCULATED",
        "calculations":[],
        "pipe_sizing":{},
        "validation":[],
    }

    scenario=_value(data,"system_arrangement")
    if scenario is None:
        out["status"]="MISSING_INPUT"
        out["calculations"].append(_result(
            "System arrangement","MISSING_INPUT",
            message="A hot-water system arrangement is required."
        ))
        return attach_pump_duty(out)

    supply=_value(data,"hot_water_supply_temperature")
    ret=_value(data,"required_return_temperature")
    length=_value(data,"total_hot_water_circulation_pipe_length")
    material=_value(data,"pipe_material")

    if supply is None or ret is None:
        out["status"]="MISSING_INPUT"
        out["calculations"].append(_result(
            "Temperature difference","MISSING_INPUT",
            formula="ΔT = T_supply - T_return",
            message="Hot-water supply and required return temperatures are required."
        ))
        return attach_pump_duty(out)

    supply_c=_temperature_to_c(supply)
    return_c=_temperature_to_c(ret)
    delta_t=supply_c-return_c

    if delta_t <= 0:
        out["status"]="INVALID"
        out["calculations"].append(_result(
            "Temperature difference","INVALID",delta_t,"K",
            "ΔT = T_supply - T_return",
            {"T_supply_C":supply_c,"T_return_C":return_c},
            "Temperature difference",
            message="Supply temperature must be greater than return temperature."
        ))
        return attach_pump_duty(out)

    out["calculations"].append(_result(
        "Temperature difference","CALCULATED",delta_t,"K",
        "ΔT = T_supply - T_return",
        {"T_supply_C":supply_c,"T_return_C":return_c},
        "Temperature difference",references=refs
    ))

    if length is None or material is None:
        out["status"]="MISSING_INPUT"
        out["calculations"].append(_result(
            "Circulation pipe basis","MISSING_INPUT",
            message="Total hot-water circulation pipe length and pipe material are required."
        ))
        return attach_pump_duty(out)

    length_m=_length_to_m(length)

    # Heat-loss basis must come from RAG; no universal W/m assumption.
    heat_loss=rag.get("heat_loss_rate_w_per_m")
    if heat_loss is None:
        out["status"]="NOT_CALCULABLE"
        out["calculations"].append(_result(
            "Hot-water heat loss","NOT_CALCULABLE",
            formula="q_total = q' × L",
            inputs={"length_m":length_m},
            message="A referenced heat-loss rate per unit pipe length is required. No universal W/m value is assumed."
        ))
        return attach_pump_duty(out)

    qprime=float(heat_loss)
    if qprime <= 0:
        raise ValueError("heat_loss_rate_w_per_m must be greater than zero.")

    q_heat=qprime*length_m
    out["calculations"].append(_result(
        "Hot-water heat loss","CALCULATED",q_heat,"W",
        "q_total = q' × L",
        {"heat_loss_rate_w_per_m":qprime,"length_m":length_m},
        "Heat-loss-based recirculation method",
        assumptions=["Heat-loss rate is supplied by the applicable referenced criterion/model."],
        references=refs
    ))

    rho=_density_kg_m3(rag,supply_c)
    cp=_cp_j_kgk(rag)
    if rho is None or cp is None:
        out["status"]="NOT_CALCULABLE"
        out["calculations"].append(_result(
            "Recirculation flow","NOT_CALCULABLE",
            formula="Q = q/(ρ cp ΔT)",
            message="Water density and specific heat at the design temperature are required from the engineering data/RAG layer."
        ))
        return attach_pump_duty(out)

    q_flow=q_heat/(rho*cp*delta_t)
    out["calculations"].append(_result(
        "Recirculation design flow","CALCULATED",q_flow,"m³/s",
        "Q = q_total/(ρ cp ΔT)",
        {"q_total_W":q_heat,"rho_kg_m3":rho,"cp_J_kgK":cp,"delta_T_K":delta_t},
        "ASHRAE heat-loss-based recirculation method",
        references=refs
    ))

    # Pipe sizing is for the circulation loop. Branch-level distribution is not
    # fabricated because the frozen UI intentionally provides only total length.
    criteria=rag.get("velocity_criteria")
    hw_c=rag.get("hazen_williams_c")
    min_v=criteria.get("min_mps") if isinstance(criteria,dict) else None
    max_v=criteria.get("max_mps") if isinstance(criteria,dict) else None

    candidates=size_pipe_candidates(
        flow_m3s=q_flow,
        material=material,
        velocity_min_mps=min_v,
        velocity_max_mps=max_v,
        hazen_williams_c=hw_c,
        length_m=length_m
    )
    selected=select_first_acceptable(candidates)

    out["pipe_sizing"]={
        "status":"CALCULATED",
        "candidate_count":len(candidates),
        "selection_status":"SELECTED" if selected else "NOT_SELECTED",
        "selected":{
            "size":selected.pipe.size_label,
            "standard":selected.pipe.standard,
            "schedule_or_sdr":selected.pipe.schedule_or_sdr,
            "inside_diameter_m":selected.pipe.inside_diameter_m,
            "velocity_mps":selected.velocity_mps,
            "head_loss_m":selected.head_loss_m,
        } if selected else None,
        "selection_message":(
            "Smallest candidate satisfying the supplied velocity criterion."
            if selected else
            "No automatic pipe selection because an applicable velocity criterion was not supplied or no candidate passed it."
        )
    }

    if selected is None or selected.head_loss_m is None:
        out["status"]="NOT_CALCULABLE"
        out["calculations"].append(_result(
            "Recirculation pump head","NOT_CALCULABLE",
            formula="Hpump = hmajor + hminor + applicable elevation/pressure terms",
            inputs={"major_loss_m":selected.head_loss_m if selected else None,
                    "minor_loss_m":None},
            message="Pump head cannot be completed until a deterministic pipe-loss value is available. Actual loop fittings/valves and applicable system configuration must also be accounted for."
        ))
    else:
        head=selected.head_loss_m
        out["calculations"].append(_result(
            "Recirculation pump head","CALCULATED",head,"m",
            "Hpump = hmajor + hminor + applicable elevation/pressure terms",
            {"major_loss_m":head,"minor_loss_m":None},
            "Available circulation-pipe major loss only",
            assumptions=["No minor-loss or branch-by-branch losses are fabricated from the frozen input set."],
            references=refs,
            message="Provisional head: actual loop fittings, valves, branches, and system configuration must be included before final issue."
        ))
        out["validation"].append({
            "name":"Recirculation-head completeness",
            "status":"WARNING",
            "severity":"WARNING",
            "message":"Only the available straight-pipe major loss is calculated. Minor and branch losses require additional deterministic system data."
        })
        hp=hydraulic_power(q_flow,head,rho)
        out["calculations"].append(_result(
            "Hydraulic power","CALCULATED",hp.value,hp.unit,
            hp.formula,hp.inputs,hp.method,references=refs
        ))

    out["calculations"].append(_result(
        "NPSH review","NOT_CALCULABLE",
        formula="NPSHa is system-derived; NPSHr is manufacturer-pump data",
        message="NPSH is not completed from the frozen recirculation inputs. Manufacturer NPSHr is required for a selected pump.",
        references=refs
    ))

    out["design_basis"]={
        "system_arrangement":scenario,
        "recirculation_basis":"Pipe heat loss",
        "domestic_hot_water_demand_used_as_pump_flow":False,
        "heat_loss_rate_source":"RAG",
    }
    return attach_pump_duty(out)
