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
    upper_factor: float | None = None

    def value(self, statistic: str) -> float:
        if statistic == "median":
            return self.factor
        if statistic == "upper":
            return self.upper_factor if self.upper_factor is not None else self.factor
        raise ValueError("statistic must be 'median' or 'upper'")


MEASURED_VENTILATION_FACTORS = (
    MeasuredVentilationFactor(1, 1, 'no-wind', 0, 1, 1),
    MeasuredVentilationFactor(1, 1, 'co-flow', 1.5, 0.687712004517809, 0.951813018119461),
    MeasuredVentilationFactor(1, 1, 'counter-flow', 1.5, 1.09092600068071, 1.09092600068071),
    MeasuredVentilationFactor(1, 1, 'co-flow', 3.5, 0.338506584137387, 0.860463671328965),
    MeasuredVentilationFactor(1, 1, 'counter-flow', 3.5, 0.965847105069752, 1.16051594360421),
    MeasuredVentilationFactor(1, 1, 'co-flow', 5, 0.31849139164131, 0.809244632438073),
    MeasuredVentilationFactor(1, 1, 'counter-flow', 5, 0.989032369869344, 1.11260844536203),
    MeasuredVentilationFactor(1, 1, 'cross-flow', 1.5, 0.555662554481104, 0.871598718778334),
    MeasuredVentilationFactor(1, 1, 'cross-flow', 3.5, 0.39628128184987, 0.93855261089995),
    MeasuredVentilationFactor(1, 1, 'cross-flow', 5, 0.369826580971089, 0.713486479579449),
    MeasuredVentilationFactor(1, 5, 'no-wind', 0, 1, 1),
    MeasuredVentilationFactor(1, 5, 'co-flow', 1.5, 0.830304534197454, 0.990712303811357),
    MeasuredVentilationFactor(1, 5, 'counter-flow', 1.5, 1.11262753798771, 1.11262753798771),
    MeasuredVentilationFactor(1, 5, 'co-flow', 3.5, 0.513167305717036, 0.822490737992286),
    MeasuredVentilationFactor(1, 5, 'counter-flow', 3.5, 1.12516603657914, 1.12516603657914),
    MeasuredVentilationFactor(1, 5, 'co-flow', 5, 0.537703075508328, 0.852277761413767),
    MeasuredVentilationFactor(1, 5, 'counter-flow', 0, 1.10045900763179, 1.1955803057227),
    MeasuredVentilationFactor(1, 1.5, 'no-wind', 0, 1, 1),
    MeasuredVentilationFactor(1, 1.5, 'cross-flow', 1.5, 0.554212094918323, 0.737328925786344),
    MeasuredVentilationFactor(1, 1.5, 'cross-flow', 3.5, 0.347637730913847, 0.63874783036359),
    MeasuredVentilationFactor(1, 1.5, 'cross-flow', 5, 0.28912398701511, 0.546167657886437),
    MeasuredVentilationFactor(4, 1, 'no-wind', 0, 1, 1),
    MeasuredVentilationFactor(4, 1, 'co-flow', 1.5, 0.566249857592151, 0.713267883862785),
    MeasuredVentilationFactor(4, 1, 'counter-flow', 1.5, 0.677911279103481, 1.00319076331884),
    MeasuredVentilationFactor(4, 1, 'co-flow', 3.5, 0.255260425117638, 0.454496878184026),
    MeasuredVentilationFactor(4, 1, 'counter-flow', 3.5, 0.66419600843745, 1.18168194805182),
    MeasuredVentilationFactor(4, 1, 'co-flow', 5, 0.160341339196721, 0.310476863031968),
    MeasuredVentilationFactor(4, 1, 'counter-flow', 5, 0.728009376736068, 1.09027603170272),
    MeasuredVentilationFactor(4, 1, 'cross-flow', 1.5, 0.396694791497647, 0.645814064453167),
    MeasuredVentilationFactor(4, 1, 'cross-flow', 3.5, 0.190310788926961, 0.643760500211111),
    MeasuredVentilationFactor(4, 1, 'cross-flow', 5, 0.221192138378944, 0.544754009601044),
    MeasuredVentilationFactor(4, 5, 'no-wind', 0, 1, 1),
    MeasuredVentilationFactor(4, 5, 'co-flow', 1.5, 0.924781753350547, 0.924781753350547),
    MeasuredVentilationFactor(4, 5, 'counter-flow', 1.5, 1.28011198741557, 1.28011198741557),
    MeasuredVentilationFactor(4, 5, 'co-flow', 3.5, 0.666226074839133, 0.740740691442013),
    MeasuredVentilationFactor(4, 5, 'counter-flow', 3.5, 1.08371293515152, 1.08371293515152),
    MeasuredVentilationFactor(4, 5, 'co-flow', 5, 0.646104738874934, 0.753916561611519),
    MeasuredVentilationFactor(4, 5, 'counter-flow', 5, 1.13202493199678, 1.13202493199678),
    MeasuredVentilationFactor(4, 2.5, 'no-wind', 0, 1, 1),
    MeasuredVentilationFactor(4, 2.5, 'cross-flow', 1.5, 0.651201371021402, 0.982456486895275),
    MeasuredVentilationFactor(4, 2.5, 'cross-flow', 3.5, 0.487313020347531, 0.828382032392462),
    MeasuredVentilationFactor(4, 2.5, 'cross-flow', 5, 0.44807752098663, 0.792012802472202),
)


def measured_ventilation_factor(
    *,
    diameter_m: float | None,
    release_g_s: float | None,
    wind_mode: str,
    wind_speed_m_s: float,
    statistic: str = "median",
) -> float:
    """Return a nearest-neighbour measured concentration ratio.

    Matching is restricted to the same wind mode.  Diameter and release rate
    are nearest-neighbour selectors; speed is linearly interpolated between
    the two nearest available speeds for that diameter/release pair.  Missing
    data deliberately return 1.0 so the proxy remains conservative and
    deterministic rather than inventing a fitted relationship.
    """
    if statistic not in {"median", "upper"}:
        raise ValueError("statistic must be 'median' or 'upper'")
    if (
        diameter_m is None
        or release_g_s is None
        or wind_mode not in {"no-wind", "co-flow", "counter-flow", "cross-flow"}
    ):
        return 1.0
    diameter_mm = max(0.1, float(diameter_m) * 1000.0)
    release = max(0.0, float(release_g_s))
    speed = max(0.0, float(wind_speed_m_s))
    candidates = [row for row in MEASURED_VENTILATION_FACTORS if row.wind_mode == wind_mode]
    if not candidates:
        return 1.0
    pairs = {(row.diameter_mm, row.release_g_s) for row in candidates}
    diameter_release = min(
        pairs,
        key=lambda pair: (
            abs(pair[0] - diameter_mm) / max(diameter_mm, 1.0)
            + abs(pair[1] - release) / max(release, 1.0)
        ),
    )
    selected = [row for row in candidates if (row.diameter_mm, row.release_g_s) == diameter_release]
    selected.sort(key=lambda row: row.wind_speed_m_s)
    if len(selected) == 1:
        factor = selected[0].value(statistic)
    elif speed <= selected[0].wind_speed_m_s:
        factor = selected[0].value(statistic)
    elif speed >= selected[-1].wind_speed_m_s:
        factor = selected[-1].value(statistic)
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
        lower_value = lower.value(statistic)
        upper_value = upper.value(statistic)
        factor = lower_value + weight * (upper_value - lower_value)
    return max(0.25, min(1.25, float(factor)))

__all__ = ["MeasuredVentilationFactor", "MEASURED_VENTILATION_FACTORS", "measured_ventilation_factor"]
