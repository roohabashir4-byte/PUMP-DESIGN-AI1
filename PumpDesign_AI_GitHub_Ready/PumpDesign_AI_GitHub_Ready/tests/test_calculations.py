from calculations.hydraulics import (
    area_from_diameter, velocity, hazen_williams_head_loss, static_head,
    hydraulic_power, pump_input_power, npsh_available
)
from calculations.demand import transfer_flow, demand_from_population
from calculations.units import gpm_to_m3s


def test_transfer_flow():
    r = transfer_flow(25000, 90)
    assert abs(r.flow - 277.7777778) < 1e-6


def test_population_demand():
    r = demand_from_population(1267, 20)
    assert r.flow == 25340


def test_area_and_velocity():
    a = area_from_diameter(0.1).value
    assert abs(a - 0.0078539816) < 1e-9
    v = velocity(gpm_to_m3s(100), 0.1).value
    assert v > 0


def test_hazen_williams():
    r = hazen_williams_head_loss(gpm_to_m3s(100), 0.1, 30, 140)
    assert r.value > 0


def test_static_head():
    assert static_head(-6, 48).value == 54


def test_power():
    q = gpm_to_m3s(100)
    assert hydraulic_power(q, 30).value > 0
    assert pump_input_power(q, 30, 0.7).value > hydraulic_power(q, 30).value


def test_npsha_can_be_negative_without_hiding_it():
    r = npsh_available(101325, 2300, 0, 10, 3, 1)
    assert r.value < 0
