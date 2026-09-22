"""Engineering unit conversions used by PumpDesign AI."""
from __future__ import annotations

from math import pi

G = 9.80665
PA_PER_PSI = 6894.757293168
M_PER_FT = 0.3048
MM_PER_IN = 25.4
L_PER_US_GAL = 3.785411784
M3_PER_US_GAL = L_PER_US_GAL / 1000.0
M3S_PER_GPM = 0.0000630901964
W_PER_KW = 1000.0
W_PER_HP = 745.699872


def ft_to_m(value_ft: float) -> float: return value_ft * M_PER_FT
def m_to_ft(value_m: float) -> float: return value_m / M_PER_FT
def inch_to_mm(value_in: float) -> float: return value_in * MM_PER_IN
def mm_to_m(value_mm: float) -> float: return value_mm / 1000.0
def us_gal_to_m3(value_gal: float) -> float: return value_gal * M3_PER_US_GAL
def m3_to_us_gal(value_m3: float) -> float: return value_m3 / M3_PER_US_GAL
def gpm_to_m3s(value_gpm: float) -> float: return value_gpm * M3S_PER_GPM
def m3s_to_gpm(value_m3s: float) -> float: return value_m3s / M3S_PER_GPM
def psi_to_pa(value_psi: float) -> float: return value_psi * PA_PER_PSI
def pa_to_psi(value_pa: float) -> float: return value_pa / PA_PER_PSI
def kw_to_w(value_kw: float) -> float: return value_kw * W_PER_KW
def hp_to_w(value_hp: float) -> float: return value_hp * W_PER_HP
