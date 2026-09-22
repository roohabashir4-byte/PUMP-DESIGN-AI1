"""Demand and transfer-flow calculations."""
from __future__ import annotations
from dataclasses import dataclass
from .units import us_gal_to_m3

@dataclass(frozen=True)
class FlowResult:
    flow: float
    unit: str
    formula: str
    inputs: dict[str, float]
    method: str

def demand_from_population(population: float, per_capita_gpd: float) -> FlowResult:
    if population <= 0 or per_capita_gpd <= 0:
        raise ValueError("Population and per-capita demand must be greater than zero.")
    total_gpd = population * per_capita_gpd
    return FlowResult(total_gpd, "US gal/day", "Demand = Population × per-capita demand", {"population": population, "per_capita_gpd": per_capita_gpd}, "Population demand")

def transfer_flow(volume_us_gal: float, time_min: float) -> FlowResult:
    if volume_us_gal <= 0 or time_min <= 0:
        raise ValueError("Transfer volume and time must be greater than zero.")
    return FlowResult(volume_us_gal / time_min, "US gal/min", "Q = V/t", {"volume_gal": volume_us_gal, "time_min": time_min}, "Transfer volume / transfer time")
