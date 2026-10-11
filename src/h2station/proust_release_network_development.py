"""Proust apparatus geometry adapter for development-only studies.

The Proust/Jamois/Studer description gives a nominal 25 L source vessel, a
10 m supply line with 10 mm nominal diameter, three terminal orifices, and an
approximately 0.1 s valve opening.  This module turns those published
dimensions into :class:`~h2station.release_network.ReleaseNetworkInputs` so
the apparatus-resolved model can be exercised without copying geometry into
ad-hoc notebooks.

This is deliberately *not* a validator and is not wired into the station
runtime.  The published source does not provide a reusable synchronized
transient logger archive, as-built bore/dead volume, or a complete valve
trace.  The returned input therefore remains a development scenario and must
not be presented as a Proust validation result.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite, pi

from .release_network import ReleaseNetworkInputs


@dataclass(frozen=True, slots=True)
class ProustApparatusGeometry:
    """Nominal apparatus dimensions reported by the Proust campaign.

    The line volume is derived from nominal length and diameter only.  It is
    not a measured dead volume and should be replaced when an as-built
    geometry record is available.
    """

    source_volume_m3: float = 0.025
    supply_line_length_m: float = 10.0
    supply_line_diameter_m: float = 0.010
    valve_opening_time_s: float = 0.1

    def __post_init__(self) -> None:
        values = {
            "source_volume_m3": self.source_volume_m3,
            "supply_line_length_m": self.supply_line_length_m,
            "supply_line_diameter_m": self.supply_line_diameter_m,
            "valve_opening_time_s": self.valve_opening_time_s,
        }
        for name, value in values.items():
            if not isfinite(value) or value <= 0.0:
                raise ValueError(f"{name} must be positive and finite")

    @property
    def supply_line_volume_m3(self) -> float:
        """Nominal cylindrical internal volume derived from published geometry."""

        return pi * self.supply_line_diameter_m**2 * self.supply_line_length_m / 4.0

    def to_network_inputs(
        self,
        *,
        source_pressure_pa_abs: float,
        source_temperature_k: float,
        terminal_diameter_m: float,
        line_initial_pressure_pa_abs: float = 101_325.0,
        line_initial_temperature_k: float = 293.15,
        upstream_discharge_coefficient: float = 1.0,
        terminal_discharge_coefficient: float = 0.8,
        line_segments: int = 1,
        intersegment_diameter_m: float | None = None,
        intersegment_discharge_coefficient: float = 1.0,
    ) -> ReleaseNetworkInputs:
        """Create a development network input for one terminal-orifice case.

        Discharge coefficients and any multi-segment restriction are explicit
        arguments because the paper does not identify them.  The terminal
        coefficient default mirrors the existing direct-aperture development
        evaluator; it is a modelling convention, not a measured Proust value.
        """

        return ReleaseNetworkInputs(
            source_volume_m3=self.source_volume_m3,
            source_pressure_pa_abs=source_pressure_pa_abs,
            source_temperature_k=source_temperature_k,
            line_volume_m3=self.supply_line_volume_m3,
            line_initial_pressure_pa_abs=line_initial_pressure_pa_abs,
            line_initial_temperature_k=line_initial_temperature_k,
            upstream_diameter_m=self.supply_line_diameter_m,
            upstream_discharge_coefficient=upstream_discharge_coefficient,
            terminal_diameter_m=terminal_diameter_m,
            terminal_discharge_coefficient=terminal_discharge_coefficient,
            valve_opening_time_s=self.valve_opening_time_s,
            terminal_valve_initial_fraction=1.0,
            terminal_valve_opening_time_s=0.0,
            line_segments=line_segments,
            intersegment_diameter_m=intersegment_diameter_m,
            intersegment_discharge_coefficient=intersegment_discharge_coefficient,
        )


def proust_terminal_diameter_m(nominal_diameter_mm: float) -> float:
    """Convert one of the published 1/2/3 mm terminal cases to metres."""

    if nominal_diameter_mm not in (1.0, 2.0, 3.0):
        raise ValueError("Proust terminal diameter must be one of 1, 2 or 3 mm")
    return nominal_diameter_mm * 1.0e-3


__all__ = ["ProustApparatusGeometry", "proust_terminal_diameter_m"]
