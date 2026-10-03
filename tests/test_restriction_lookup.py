"""The fast choking lookup must preserve the original real-gas flow curve."""

from math import exp, log, sqrt

import pytest
from scipy.optimize import minimize_scalar

from h2station.dispenser import IsentropicRealGasRestriction, RestrictionParameters
from h2station.tabulated import hydrogen_table


@pytest.mark.parametrize("pressure_mpa,temperature_k", [
    (0.2, 210.0),
    (2.0, 243.0), (15.0, 333.0), (45.0, 298.0), (70.0, 243.0),
    (90.0, 333.0), (110.0, 390.0), (120.0, 500.0),
    (30.0, 190.0), (30.0, 550.0),
])
@pytest.mark.parametrize("backpressure_ratio", [0.1, 0.45, 0.55, 0.9])
def test_fast_restriction_matches_direct_choking_search(
    pressure_mpa: float, temperature_k: float, backpressure_ratio: float,
) -> None:
    table = hydrogen_table()
    pressure = pressure_mpa * 1.0e6
    downstream = pressure * backpressure_ratio
    lower_pressure = max(1.0e5, downstream)
    upstream = table.state_pt(pressure, temperature_k)

    def mass_flux(outlet_pressure: float) -> float:
        outlet = table.state_ps(outlet_pressure, upstream.entropy)
        return outlet.density * sqrt(max(0.0, 2.0 * (upstream.enthalpy - outlet.enthalpy)))

    optimum = minimize_scalar(
        lambda log_pressure: -mass_flux(exp(log_pressure)),
        bounds=(log(lower_pressure), log(pressure)),
        method="bounded",
        options={"xatol": 1.0e-8},
    )
    reference_flux = max(mass_flux(lower_pressure), -optimum.fun)
    parameters = RestrictionParameters(flow_area_m2=1.0e-8, discharge_coefficient=0.8)
    actual = IsentropicRealGasRestriction(parameters).mass_flow_kg_s(
        pressure, temperature_k, downstream
    )
    assert actual == pytest.approx(0.8e-8 * reference_flux, rel=2.0e-4)


def test_deep_expansion_uses_admissible_table_boundary():
    """Cold blowdown remains finite when the sonic point is below the P-s table."""
    restriction = IsentropicRealGasRestriction(
        RestrictionParameters(flow_area_m2=1.0e-8, discharge_coefficient=0.8)
    )
    # This state is reached late in the public PRESLHY 0.5 mm blowdown
    # trace. The mathematical choking point is below the represented entropy
    # curve, but the lower admissible table boundary still gives a bounded
    # conservative mass flux.
    flow = restriction.mass_flow_kg_s(313508.43, 79.56074, 101325.0)
    assert flow > 0.0
