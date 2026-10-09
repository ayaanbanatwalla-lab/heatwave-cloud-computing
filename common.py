"""Shared constants: regions and a SIMPLIFIED version of IMD heatwave criteria."""
import math

# 7 illustrative regions (simplified; NOT the official IMD region split).
# type decides the absolute temperature threshold used by the rule.
REGIONS = {
    "Northwest":       {"type": "plains",  "base": 31.0, "amp": 9.0, "peak_doy": 160},
    "Central":         {"type": "plains",  "base": 32.0, "amp": 7.5, "peak_doy": 145},
    "East":            {"type": "plains",  "base": 31.0, "amp": 5.5, "peak_doy": 140},
    "Northeast":       {"type": "plains",  "base": 28.0, "amp": 4.0, "peak_doy": 200},
    "South Peninsula": {"type": "plains",  "base": 32.0, "amp": 3.5, "peak_doy": 120},
    "West Coast":      {"type": "coastal", "base": 31.0, "amp": 3.0, "peak_doy": 125},
    "Hills":           {"type": "hills",   "base": 20.0, "amp": 7.0, "peak_doy": 165},
}
REGION_LIST = list(REGIONS)
THRESH = {"plains": 40.0, "coastal": 37.0, "hills": 30.0}
LABELS = ["Normal", "Heatwave", "Severe Heatwave"]


def normal_temp(region: str, doy: int) -> float:
    r = REGIONS[region]
    return r["base"] + r["amp"] * math.cos(2 * math.pi * (doy - r["peak_doy"]) / 365.0)


def imd_rule(region: str, tmax: float, normal: float) -> int:
    """Simplified IMD-style rule. 0=Normal, 1=Heatwave, 2=Severe.
    Heatwave: Tmax >= regional threshold AND departure >= 4.5 C (or Tmax >= 45 C).
    Severe:   departure >= 6.5 C (with threshold met) or Tmax >= 47 C."""
    dep = tmax - normal
    thr = THRESH[REGIONS[region]["type"]]
    if tmax >= 47 or (tmax >= thr and dep >= 6.5):
        return 2
    if tmax >= 45 or (tmax >= thr and dep >= 4.5):
        return 1
    return 0
