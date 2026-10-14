from h2station.risk.consequence_uncertainty import consequence_uncertainty_screen
from h2station.risk.live import HyRAMDynamicReleaseRequest


def request():
    return HyRAMDynamicReleaseRequest(
        release_id="test", component_id="cascade.high", location="N09",
        time_s=1, duration_s=1, source_pressure_pa=70e6,
        source_temperature_k=288.15, ambient_pressure_pa=101325,
        orifice_diameter_m=.001, discharge_coefficient=.8,
        mass_flow_override_kg_s=.03, cumulative_released_mass_kg=.03,
        release_angle_rad=0, release_height_m=1.5, indoor=False,
        annual_frequency_per_year=None, immediate_ignition_probability=None,
        delayed_ignition_probability=None,
    )


def fake_evaluator(sample):
    flow = sample.mass_flow_override_kg_s
    return {
        "mass_flow_override_kg_s": flow,
        "sampled_effect_radius_m": 3 + 80 * flow,
        "maximum_heat_flux_w_m2": 100000 * flow,
        "maximum_overpressure_pa": 50000 * flow,
    }


def test_bounded_screen_is_reproducible_and_reports_percentiles_and_sensitivity():
    first = consequence_uncertainty_screen(fake_evaluator, request(), sample_count=24)
    second = consequence_uncertainty_screen(fake_evaluator, request(), sample_count=24)
    assert first == second
    radius = first["percentiles"]["sampled_effect_radius_m"]
    assert radius["p05"] < radius["p50"] < radius["p95"]
    assert first["sensitivity_ranking"][0]["input"] == "orifice_diameter_m"
    assert "not statistical confidence intervals" in first["claim_limit"]


def test_sample_count_and_bounds_are_guarded():
    import pytest
    with pytest.raises(ValueError, match="sample_count"):
        consequence_uncertainty_screen(fake_evaluator, request(), sample_count=4)
    with pytest.raises(ValueError, match="bounds"):
        consequence_uncertainty_screen(fake_evaluator, request(), pressure_relative=-.1)
