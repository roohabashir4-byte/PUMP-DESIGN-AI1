"""Deterministic pipe registry and pipe sizing engine.

The LLM may choose the sizing workflow, material, and applicable criteria, but
this module owns candidate generation, hydraulic calculations, and validation.
Registry values are traceable to their stated source metadata; they are not
permission to invent dimensions when a project-specific product standard is
required.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Iterable, Optional

from .hydraulics import hazen_williams_head_loss, velocity
from .units import MM_PER_IN, mm_to_m


@dataclass(frozen=True)
class PipeRecord:
    material: str
    standard: str
    size_label: str
    nominal_size: Optional[float]
    nominal_unit: str
    schedule_or_sdr: Optional[str]
    outside_diameter_m: float
    wall_thickness_m: float
    inside_diameter_m: float
    source_status: str = "registry_value_requires_project_product_verification"
    notes: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


# Common IPS/NPS outside diameters in inches.  Values below are intentionally
# stored explicitly rather than inferred from nominal size.
_STEEL_OD_IN = {
    0.5: 0.840, 0.75: 1.050, 1.0: 1.315, 1.25: 1.660, 1.5: 1.900,
    2.0: 2.375, 2.5: 2.875, 3.0: 3.500, 3.5: 4.000, 4.0: 4.500,
    5.0: 5.563, 6.0: 6.625, 8.0: 8.625, 10.0: 10.750, 12.0: 12.750,
    14.0: 14.000, 16.0: 16.000, 18.0: 18.000, 20.0: 20.000,
    22.0: 22.000, 24.0: 24.000,
}

# ASME B36.10 common carbon-steel wall thicknesses (in) for Sch 40/80.
# The registry is deliberately explicit so it can later be replaced by a
# licensed/project-approved table without changing the sizing engine.
_STEEL_WALL_IN = {
    "40": {0.5: .109, .75: .113, 1.0: .133, 1.25: .140, 1.5: .145,
            2.0: .154, 2.5: .203, 3.0: .216, 3.5: .226, 4.0: .237,
            5.0: .258, 6.0: .280, 8.0: .322, 10.0: .365, 12.0: .375,
            14.0: .375, 16.0: .375, 18.0: .375, 20.0: .375, 22.0: .375, 24.0: .375},
    "80": {0.5: .147, .75: .154, 1.0: .179, 1.25: .191, 1.5: .200,
            2.0: .218, 2.5: .276, 3.0: .300, 3.5: .318, 4.0: .337,
            5.0: .375, 6.0: .432, 8.0: .500, 10.0: .593, 12.0: .687,
            14.0: .750, 16.0: .843, 18.0: .937, 20.0: 1.031, 22.0: 1.125, 24.0: 1.218},
}

# ASTM D1785 IPS PVC schedules. The outside diameters are the same nominal
# IPS series; walls are represented for the common sizes used in this engine.
_PVC_WALL_IN = {
    "40": {0.5:.109, .75:.113, 1:.133, 1.25:.140, 1.5:.145, 2:.154,
           2.5:.203, 3:.216, 4:.237, 5:.258, 6:.280, 8:.322, 10:.365, 12:.406},
    "80": {0.5:.147, .75:.154, 1:.179, 1.25:.191, 1.5:.200, 2:.218,
           2.5:.276, 3:.300, 4:.337, 5:.375, 6:.432, 8:.500, 10:.593, 12:.687},
}


def _ips_records(material: str, standard: str, walls: dict[str, dict[float, float]]) -> list[PipeRecord]:
    records: list[PipeRecord] = []
    for sched, table in walls.items():
        for nominal, wall_in in table.items():
            od = _STEEL_OD_IN[nominal] * (MM_PER_IN / 1000.0)
            wall = wall_in * (MM_PER_IN / 1000.0)
            records.append(PipeRecord(
                material=material,
                standard=standard,
                size_label=f'NPS {nominal:g}',
                nominal_size=nominal,
                nominal_unit="in",
                schedule_or_sdr=f"Sch {sched}",
                outside_diameter_m=od,
                wall_thickness_m=wall,
                inside_diameter_m=od - 2 * wall,
                notes="Nominal/actual dimensions must be confirmed against the selected product and applicable edition.",
            ))
    return records


def _od_metric_records(material: str, standard: str, sizes_mm: Iterable[int], sdr_values: Iterable[float]) -> list[PipeRecord]:
    records: list[PipeRecord] = []
    for od_mm in sizes_mm:
        for sdr in sdr_values:
            wall_mm = od_mm / sdr
            records.append(PipeRecord(
                material=material,
                standard=standard,
                size_label=f"DN/OD {od_mm} mm",
                nominal_size=float(od_mm),
                nominal_unit="mm",
                schedule_or_sdr=f"SDR {sdr:g}",
                outside_diameter_m=od_mm * 0.001,
                wall_thickness_m=wall_mm * 0.001,
                inside_diameter_m=(od_mm - 2 * wall_mm) * 0.001,
                notes="ID derived from OD and SDR; confirm applicable ISO/product series and tolerance before issue.",
            ))
    return records


def _ppr_records() -> list[PipeRecord]:
    records: list[PipeRecord] = []
    # Common ISO 15874 OD series. Wall = OD/(2*S), ID = OD - 2t.
    sizes = [20, 25, 32, 40, 50, 63, 75, 90, 110, 125, 140, 160]
    for od_mm in sizes:
        for s in (5.0, 3.2, 2.5):
            wall_mm = od_mm / (2 * s + 1)
            records.append(PipeRecord(
                material="PP-R",
                standard="ISO 15874-2:2013",
                size_label=f"DN/OD {od_mm} mm",
                nominal_size=float(od_mm),
                nominal_unit="mm",
                schedule_or_sdr=f"S {s:g}",
                outside_diameter_m=od_mm * 0.001,
                wall_thickness_m=wall_mm * 0.001,
                inside_diameter_m=(od_mm - 2 * wall_mm) * 0.001,
                notes="ID derived from OD and ISO series S relationship; confirm manufacturer dimensional table.",
            ))
    return records


def default_pipe_registry() -> list[PipeRecord]:
    records = []
    records.extend(_ips_records("MS/carbon steel", "ASME B36.10", _STEEL_WALL_IN))
    records.extend(_ips_records("PVC-U", "ASTM D1785", _PVC_WALL_IN))
    records.extend(_od_metric_records("HDPE/PE100", "ISO 4427-2:2019", [20,25,32,40,50,63,75,90,110,125,140,160,180,200,225,250,280,315,355,400], [11,17]))
    records.extend(_ppr_records())
    return records


class PipeRegistry:
    def __init__(self, records: Optional[Iterable[PipeRecord]] = None):
        self.records = list(records if records is not None else default_pipe_registry())

    def find(self, material: str, size_label: str | None = None, schedule_or_sdr: str | None = None) -> list[PipeRecord]:
        out = [r for r in self.records if r.material.lower() == material.lower()]
        if size_label is not None:
            out = [r for r in out if r.size_label.lower() == size_label.lower()]
        if schedule_or_sdr is not None:
            out = [r for r in out if r.schedule_or_sdr.lower() == schedule_or_sdr.lower()]
        return out

    def materials(self) -> list[str]:
        return sorted({r.material for r in self.records})


@dataclass(frozen=True)
class PipeSizingCandidate:
    pipe: PipeRecord
    flow_m3s: float
    velocity_mps: float
    head_loss_m: Optional[float]
    velocity_status: str
    hydraulic_status: str
    applicable: bool
    reason: str


def size_pipe_candidates(
    flow_m3s: float,
    material: str,
    *,
    registry: Optional[PipeRegistry] = None,
    velocity_min_mps: Optional[float] = None,
    velocity_max_mps: Optional[float] = None,
    hazen_williams_c: Optional[float] = None,
    length_m: Optional[float] = None,
    schedule_or_sdr: Optional[str] = None,
    max_head_loss_m: Optional[float] = None,
    max_head_loss_per_100m_m: Optional[float] = None,
) -> list[PipeSizingCandidate]:
    """Generate deterministic candidates; criteria themselves come from RAG/config.

    No universal velocity limit is embedded here. If no velocity criterion is
    supplied, the result is marked NOT_CHECKED rather than inventing one.
    """
    if flow_m3s <= 0:
        raise ValueError("flow_m3s must be greater than zero")
    if max_head_loss_m is not None and max_head_loss_m < 0:
        raise ValueError("max_head_loss_m cannot be negative")
    if max_head_loss_per_100m_m is not None and max_head_loss_per_100m_m < 0:
        raise ValueError("max_head_loss_per_100m_m cannot be negative")
    if max_head_loss_m is not None and max_head_loss_per_100m_m is not None:
        raise ValueError("Supply only one hydraulic head-loss criterion")
    reg = registry or PipeRegistry()
    records = reg.find(material, schedule_or_sdr=schedule_or_sdr)
    if not records:
        raise ValueError(f"No pipe registry records found for material: {material}")

    candidates = []
    for pipe in sorted(records, key=lambda r: r.inside_diameter_m):
        v = velocity(flow_m3s, pipe.inside_diameter_m).value
        if velocity_min_mps is None and velocity_max_mps is None:
            v_status = "NOT_CHECKED"
            v_ok = True
            v_reason = "No velocity criterion supplied."
        else:
            low_ok = velocity_min_mps is None or v >= velocity_min_mps
            high_ok = velocity_max_mps is None or v <= velocity_max_mps
            v_ok = low_ok and high_ok
            v_status = "PASS" if v_ok else "FAIL"
            v_reason = "Velocity criterion satisfied." if v_ok else "Velocity outside supplied criterion."

        loss = None
        if hazen_williams_c is not None:
            if length_m is None:
                h_status = "NOT_CHECKED"
                h_reason = "Hazen-Williams C supplied but length is missing."
            else:
                loss = hazen_williams_head_loss(flow_m3s, pipe.inside_diameter_m, length_m, hazen_williams_c).value
                if max_head_loss_m is not None:
                    h_ok = loss <= max_head_loss_m
                    h_status = "PASS" if h_ok else "FAIL"
                    h_reason = "Total head-loss criterion satisfied." if h_ok else "Total head-loss criterion exceeded."
                elif max_head_loss_per_100m_m is not None:
                    normalized = loss / length_m * 100.0 if length_m > 0 else 0.0
                    h_ok = normalized <= max_head_loss_per_100m_m
                    h_status = "PASS" if h_ok else "FAIL"
                    h_reason = "Head-loss-per-100m criterion satisfied." if h_ok else "Head-loss-per-100m criterion exceeded."
                else:
                    h_status = "CALCULATED"
                    h_reason = "Hazen-Williams loss calculated; no hydraulic acceptance criterion supplied."
        else:
            h_status = "NOT_CHECKED"
            h_reason = "No Hazen-Williams C supplied."

        candidates.append(PipeSizingCandidate(
            pipe=pipe,
            flow_m3s=flow_m3s,
            velocity_mps=v,
            head_loss_m=loss,
            velocity_status=v_status,
            hydraulic_status=h_status,
            applicable=(v_ok and h_status in {"CALCULATED", "PASS", "NOT_CHECKED"}),
            reason=f"{v_reason} {h_reason}",
        ))
    return candidates


def select_first_acceptable(candidates: list[PipeSizingCandidate]) -> PipeSizingCandidate | None:
    """Legacy velocity-based selector retained for existing workflows.

    Production automatic selection should use ``select_with_acceptance_criteria``
    once the applicable hydraulic acceptance criterion is available.
    """
    for candidate in candidates:
        if candidate.applicable and candidate.velocity_status != "NOT_CHECKED":
            return candidate
    return None


def select_with_acceptance_criteria(candidates: list[PipeSizingCandidate]) -> PipeSizingCandidate | None:
    """Select the smallest candidate satisfying velocity and hydraulic checks.

    If hydraulic loss is only calculated but has no acceptance limit, no
    automatic selection is made.
    """
    for candidate in candidates:
        if not candidate.applicable or candidate.velocity_status == "NOT_CHECKED":
            continue
        if candidate.hydraulic_status in {"PASS", "FAIL"}:
            if candidate.hydraulic_status == "PASS":
                return candidate
            continue
        if candidate.hydraulic_status == "NOT_CHECKED":
            continue
        # CALCULATED means loss is available but no acceptance limit exists.
        continue
    return None
