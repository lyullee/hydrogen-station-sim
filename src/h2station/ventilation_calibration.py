"""Data-derived ventilation adjustment from the public Grune/Sempert archive.

The table is intentionally low-dimensional: it is a bounded empirical envelope
for the virtual detector proxy, not a CFD model or detector certification.
"""

from __future__ import annotations

from dataclasses import dataclass

@dataclass(frozen=True)
class MeasuredVentilationFactor:
    diameter_mm: float
    release_g_s: float
    wind_mode: str
    wind_speed_m_s: float
    factor: float


MEASURED_VENTILATION_FACTORS = (
    MeasuredVentilationFactor(1.0, 1.0, 'no-wind', 0.0, 1.0),
    MeasuredVentilationFactor(1.0, 1.0, 'co-flow', 1.5, 0.6877120045178091),
    MeasuredVentilationFactor(1.0, 1.0, 'counter-flow', 1.5, 1.0909260006807078),
    MeasuredVentilationFactor(1.0, 1.0, 'co-flow', 3.5, 0.33850658413738693),
    MeasuredVentilationFactor(1.0, 1.0, 'counter-flow', 3.5, 0.9658471050697521),
    MeasuredVentilationFactor(1.0, 1.0, 'co-flow', 5.0, 0.3184913916413096),
    MeasuredVentilationFactor(1.0, 1.0, 'counter-flow', 5.0, 0.9890323698693438),
    MeasuredVentilationFactor(1.0, 1.0, 'cross-flow', 1.5, 0.555662554481104),
    MeasuredVentilationFactor(1.0, 1.0, 'cross-flow', 3.5, 0.3962812818498697),
    MeasuredVentilationFactor(1.0, 1.0, 'cross-flow', 5.0, 0.36982658097108917),
    MeasuredVentilationFactor(1.0, 5.0, 'no-wind', 0.0, 1.0),
    MeasuredVentilationFactor(1.0, 5.0, 'co-flow', 1.5, 0.8303045341974536),
    MeasuredVentilationFactor(1.0, 5.0, 'counter-flow', 1.5, 1.1126275379877102),
    MeasuredVentilationFactor(1.0, 5.0, 'co-flow', 3.5, 0.5131673057170362),
    MeasuredVentilationFactor(1.0, 5.0, 'counter-flow', 3.5, 1.125166036579136),
    MeasuredVentilationFactor(1.0, 5.0, 'co-flow', 5.0, 0.5377030755083275),
    MeasuredVentilationFactor(1.0, 5.0, 'counter-flow', 0.0, 1.1004590076317882),
    MeasuredVentilationFactor(1.0, 1.5, 'no-wind', 0.0, 1.0),
    MeasuredVentilationFactor(1.0, 1.5, 'cross-flow', 1.5, 0.5542120949183234),
    MeasuredVentilationFactor(1.0, 1.5, 'cross-flow', 3.5, 0.34763773091384664),
    MeasuredVentilationFactor(1.0, 1.5, 'cross-flow', 5.0, 0.2891239870151101),
    MeasuredVentilationFactor(4.0, 1.0, 'no-wind', 0.0, 1.0),
    MeasuredVentilationFactor(4.0, 1.0, 'co-flow', 1.5, 0.5662498575921509),
    MeasuredVentilationFactor(4.0, 1.0, 'counter-flow', 1.5, 0.6779112791034813),
    MeasuredVentilationFactor(4.0, 1.0, 'co-flow', 3.5, 0.2552604251176376),
    MeasuredVentilationFactor(4.0, 1.0, 'counter-flow', 3.5, 0.6641960084374495),
    MeasuredVentilationFactor(4.0, 1.0, 'co-flow', 5.0, 0.1603413391967205),
    MeasuredVentilationFactor(4.0, 1.0, 'counter-flow', 5.0, 0.7280093767360676),
    MeasuredVentilationFactor(4.0, 1.0, 'cross-flow', 1.5, 0.39669479149764725),
    MeasuredVentilationFactor(4.0, 1.0, 'cross-flow', 3.5, 0.1903107889269614),
    MeasuredVentilationFactor(4.0, 1.0, 'cross-flow', 5.0, 0.22119213837894405),
    MeasuredVentilationFactor(4.0, 5.0, 'no-wind', 0.0, 1.0),
    MeasuredVentilationFactor(4.0, 5.0, 'co-flow', 1.5, 0.9247817533505474),
    MeasuredVentilationFactor(4.0, 5.0, 'counter-flow', 1.5, 1.2801119874155655),
    MeasuredVentilationFactor(4.0, 5.0, 'co-flow', 3.5, 0.6662260748391328),
    MeasuredVentilationFactor(4.0, 5.0, 'counter-flow', 3.5, 1.083712935151519),
    MeasuredVentilationFactor(4.0, 5.0, 'co-flow', 5.0, 0.6461047388749345),
    MeasuredVentilationFactor(4.0, 5.0, 'counter-flow', 5.0, 1.1320249319967814),
    MeasuredVentilationFactor(4.0, 2.5, 'no-wind', 0.0, 1.0),
    MeasuredVentilationFactor(4.0, 2.5, 'cross-flow', 1.5, 0.6512013710214015),
    MeasuredVentilationFactor(4.0, 2.5, 'cross-flow', 3.5, 0.4873130203475315),
    MeasuredVentilationFactor(4.0, 2.5, 'cross-flow', 5.0, 0.44807752098663045),
)

def measured_ventilation_factor(*, diameter_m: float | None, release_g_s: float | None, wind_mode: str, wind_speed_m_s: float) -> float:
    """Return a nearest-neighbour measured concentration ratio.

    Matching is restricted to the same wind mode.  Diameter and release rate
    are nearest-neighbour selectors; speed is linearly interpolated between
    the two nearest available speeds for that diameter/release pair.  Missing
    data deliberately return 1.0 so the proxy remains conservative and
    deterministic rather than inventing a fitted relationship.
    """
    if diameter_m is None or release_g_s is None or wind_mode not in {"no-wind", "co-flow", "counter-flow", "cross-flow"}:
        return 1.0
    diameter_mm = max(0.1, float(diameter_m) * 1000.0)
    release = max(0.0, float(release_g_s))
    speed = max(0.0, float(wind_speed_m_s))
    candidates = [row for row in MEASURED_VENTILATION_FACTORS if row.wind_mode == wind_mode]
    if not candidates:
        return 1.0
    pairs = {(row.diameter_mm, row.release_g_s) for row in candidates}
    diameter_release = min(pairs, key=lambda pair: abs(pair[0] - diameter_mm) / max(diameter_mm, 1.0) + abs(pair[1] - release) / max(release, 1.0))
    selected = [row for row in candidates if (row.diameter_mm, row.release_g_s) == diameter_release]
    selected.sort(key=lambda row: row.wind_speed_m_s)
    if len(selected) == 1:
        factor = selected[0].factor
    elif speed <= selected[0].wind_speed_m_s:
        factor = selected[0].factor
    elif speed >= selected[-1].wind_speed_m_s:
        factor = selected[-1].factor
    else:
        lower = max(
            (row for row in selected if row.wind_speed_m_s <= speed),
            key=lambda row: row.wind_speed_m_s,
        )
        upper = min(
            (row for row in selected if row.wind_speed_m_s >= speed),
            key=lambda row: row.wind_speed_m_s,
        )
        span = upper.wind_speed_m_s - lower.wind_speed_m_s
        weight = (speed - lower.wind_speed_m_s) / span if span else 0.0
        factor = lower.factor + weight * (upper.factor - lower.factor)
    return max(0.25, min(1.25, float(factor)))

__all__ = ["MeasuredVentilationFactor", "MEASURED_VENTILATION_FACTORS", "measured_ventilation_factor"]
