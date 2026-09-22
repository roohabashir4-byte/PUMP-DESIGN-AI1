"""Pure deterministic hydraulic calculations.

No LLM reasoning belongs in this module. Functions validate their inputs and
return engineering values that can be traced and tested independently.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

from .units import G


@dataclass(frozen=True)
class HydraulicResult:
    value: float
    unit: str
    formula: str
    inputs: dict[str, float]
    method: str


def _positive(name: str, value: float) -> None:
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be a finite value greater than zero.")


def _nonnegative(name: str, value: float) -> None:
    if not math.isfinite(value) or value < 0:
        raise ValueError(f"{name} must be a finite value greater than or equal to zero.")


def area_from_diameter(diameter_m: float) -> HydraulicResult:
    _positive("diameter_m", diameter_m)
    value = math.pi * diameter_m**2 / 4.0
    return HydraulicResult(value, "m²", "A = πD²/4", {"D": diameter_m}, "Circular pipe")


def velocity(flow_m3s: float, diameter_m: float) -> HydraulicResult:
    _positive("flow_m3s", flow_m3s)
    area = area_from_diameter(diameter_m).value
    value = flow_m3s / area
    return HydraulicResult(value, "m/s", "V = Q/A = 4Q/(πD²)", {"Q": flow_m3s, "D": diameter_m}, "Continuity")


def reynolds_number(flow_m3s: float, diameter_m: float, density_kg_m3: float = 998.0,
                    dynamic_viscosity_pa_s: float = 0.001002) -> HydraulicResult:
    _positive("flow_m3s", flow_m3s)
    _positive("diameter_m", diameter_m)
    _positive("density_kg_m3", density_kg_m3)
    _positive("dynamic_viscosity_pa_s", dynamic_viscosity_pa_s)
    v = velocity(flow_m3s, diameter_m).value
    value = density_kg_m3 * v * diameter_m / dynamic_viscosity_pa_s
    return HydraulicResult(value, "-", "Re = ρVD/μ", {"rho": density_kg_m3, "V": v, "D": diameter_m, "mu": dynamic_viscosity_pa_s}, "Reynolds")


def hazen_williams_head_loss(flow_m3s: float, diameter_m: float, length_m: float, c: float) -> HydraulicResult:
    _positive("flow_m3s", flow_m3s); _positive("diameter_m", diameter_m); _nonnegative("length_m", length_m); _positive("c", c)
    value = 10.67 * length_m * flow_m3s**1.852 / (c**1.852 * diameter_m**4.87)
    return HydraulicResult(value, "m", "hf = 10.67 L Q^1.852 /(C^1.852 D^4.87)", {"L": length_m, "Q": flow_m3s, "C": c, "D": diameter_m}, "Hazen-Williams SI")


def darcy_head_loss(flow_m3s: float, diameter_m: float, length_m: float, roughness_m: float,
                    density_kg_m3: float = 998.0, dynamic_viscosity_pa_s: float = 0.001002,
                    friction_factor: Optional[float] = None) -> HydraulicResult:
    _positive("flow_m3s", flow_m3s); _positive("diameter_m", diameter_m); _nonnegative("length_m", length_m); _nonnegative("roughness_m", roughness_m)
    re = reynolds_number(flow_m3s, diameter_m, density_kg_m3, dynamic_viscosity_pa_s).value
    if re < 2300:
        f = 64.0 / re
        method = "Darcy-Weisbach; laminar f=64/Re"
    else:
        if friction_factor is None:
            # Haaland explicit approximation to Colebrook-White.
            f = (-1.8 * math.log10(((roughness_m / diameter_m) / 3.7) ** 1.11 + 6.9 / re)) ** -2
            method = "Darcy-Weisbach; Haaland approximation to Colebrook-White"
        else:
            _positive("friction_factor", friction_factor)
            f = friction_factor
            method = "Darcy-Weisbach; supplied friction factor"
    v = velocity(flow_m3s, diameter_m).value
    value = f * (length_m / diameter_m) * (v**2 / (2 * G))
    return HydraulicResult(value, "m", "hf = f(L/D)(V²/2g)", {"L": length_m, "Q": flow_m3s, "D": diameter_m, "epsilon": roughness_m, "Re": re, "f": f}, method)


def minor_head_loss(flow_m3s: float, diameter_m: float, k_total: float) -> HydraulicResult:
    _positive("flow_m3s", flow_m3s); _positive("diameter_m", diameter_m); _nonnegative("k_total", k_total)
    v = velocity(flow_m3s, diameter_m).value
    value = k_total * v**2 / (2 * G)
    return HydraulicResult(value, "m", "hm = K V²/(2g)", {"Q": flow_m3s, "D": diameter_m, "K": k_total, "V": v}, "Minor-loss K method")


def static_head(z_source_m: float, z_destination_m: float) -> HydraulicResult:
    if not all(math.isfinite(x) for x in (z_source_m, z_destination_m)):
        raise ValueError("Elevation values must be finite.")
    value = z_destination_m - z_source_m
    return HydraulicResult(value, "m", "Hs = Z₂ - Z₁", {"Z1": z_source_m, "Z2": z_destination_m}, "Static elevation head")


def pressure_head(pressure_difference_pa: float, density_kg_m3: float = 998.0) -> HydraulicResult:
    _positive("density_kg_m3", density_kg_m3)
    if not math.isfinite(pressure_difference_pa): raise ValueError("pressure_difference_pa must be finite.")
    value = pressure_difference_pa / (density_kg_m3 * G)
    return HydraulicResult(value, "m", "ΔHp = ΔP/(ρg)", {"delta_P": pressure_difference_pa, "rho": density_kg_m3}, "Pressure head")


def pump_head(static_head_m: float, pressure_head_m: float = 0.0, velocity_head_difference_m: float = 0.0,
              major_loss_m: float = 0.0, minor_loss_m: float = 0.0) -> HydraulicResult:
    terms = [static_head_m, pressure_head_m, velocity_head_difference_m, major_loss_m, minor_loss_m]
    if not all(math.isfinite(x) for x in terms): raise ValueError("Pump-head terms must be finite.")
    if major_loss_m < 0 or minor_loss_m < 0: raise ValueError("Losses cannot be negative.")
    value = sum(terms)
    return HydraulicResult(value, "m", "Hp = ΔZ + ΔP/(ρg) + Δ(V²)/(2g) + hmajor + hminor", {"static": static_head_m, "pressure": pressure_head_m, "velocity": velocity_head_difference_m, "major": major_loss_m, "minor": minor_loss_m}, "Energy equation")


def hydraulic_power(flow_m3s: float, head_m: float, density_kg_m3: float = 998.0) -> HydraulicResult:
    _positive("flow_m3s", flow_m3s); _nonnegative("head_m", head_m); _positive("density_kg_m3", density_kg_m3)
    value = density_kg_m3 * G * flow_m3s * head_m
    return HydraulicResult(value, "W", "Ph = ρgQH", {"rho": density_kg_m3, "Q": flow_m3s, "H": head_m}, "Hydraulic power")


def pump_input_power(flow_m3s: float, head_m: float, efficiency: float, density_kg_m3: float = 998.0) -> HydraulicResult:
    _positive("flow_m3s", flow_m3s); _nonnegative("head_m", head_m); _positive("density_kg_m3", density_kg_m3)
    if not 0 < efficiency <= 1: raise ValueError("efficiency must be greater than 0 and no greater than 1.")
    value = density_kg_m3 * G * flow_m3s * head_m / efficiency
    return HydraulicResult(value, "W", "P = ρgQH/η", {"rho": density_kg_m3, "Q": flow_m3s, "H": head_m, "eta": efficiency}, "Pump input power")


def npsh_available(atmospheric_pressure_pa: float, vapor_pressure_pa: float, elevation_pressure_head_m: float,
                   suction_surface_to_pump_head_m: float, suction_loss_m: float,
                   velocity_head_m: float = 0.0, density_kg_m3: float = 998.0) -> HydraulicResult:
    _positive("atmospheric_pressure_pa", atmospheric_pressure_pa); _nonnegative("vapor_pressure_pa", vapor_pressure_pa)
    _positive("density_kg_m3", density_kg_m3); _nonnegative("suction_loss_m", suction_loss_m); _nonnegative("velocity_head_m", velocity_head_m)
    value = (atmospheric_pressure_pa - vapor_pressure_pa) / (density_kg_m3 * G) + elevation_pressure_head_m - suction_surface_to_pump_head_m - suction_loss_m - velocity_head_m
    return HydraulicResult(value, "m", "NPSHa = (Patm-Pv)/(ρg) + Hpressure - Hz - hfs - V²/(2g)", {"Patm": atmospheric_pressure_pa, "Pv": vapor_pressure_pa, "Hpressure": elevation_pressure_head_m, "Hz": suction_surface_to_pump_head_m, "hfs": suction_loss_m, "V²/2g": velocity_head_m, "rho": density_kg_m3}, "System-derived NPSHa")


def static_pressure_to_head(pressure_pa: float, density_kg_m3: float = 998.0) -> HydraulicResult:
    return pressure_head(pressure_pa, density_kg_m3)
