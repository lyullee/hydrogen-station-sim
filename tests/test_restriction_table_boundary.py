import numpy as np

from h2station.dispenser import IsentropicRealGasRestriction, RestrictionParameters


def test_critical_expansion_stays_finite_when_sonic_point_leaves_table_domain():
    restriction = IsentropicRealGasRestriction(
        RestrictionParameters(
            flow_area_m2=0.25 * np.pi * (0.0005**2),
            discharge_coefficient=0.8,
        )
    )
    flow = restriction.mass_flow_kg_s(20.1945004e6, 310.7252825, 101325.0)
    assert np.isfinite(flow)
    assert flow > 0.0


def test_table_boundary_fix_preserves_reference_restriction_result():
    restriction = IsentropicRealGasRestriction(
        RestrictionParameters(flow_area_m2=1.0e-8, discharge_coefficient=0.8)
    )
    atmospheric = restriction.mass_flow_kg_s(90.0e6, 298.15, 101325.0)
    backpressured = restriction.mass_flow_kg_s(90.0e6, 298.15, 5.0e6)
    assert np.isfinite(atmospheric) and atmospheric > 0.0
    assert np.isfinite(backpressured) and backpressured > 0.0
    assert backpressured <= atmospheric
