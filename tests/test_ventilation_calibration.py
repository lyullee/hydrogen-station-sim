import pytest

from h2station.ventilation_calibration import measured_ventilation_factor
from h2station.virtual_safety import VirtualSafetyRuntime


def test_public_measurement_factor_interpolates_and_is_bounded():
    value = measured_ventilation_factor(
        diameter_m=0.001,
        release_g_s=5.0,
        wind_mode="co-flow",
        wind_speed_m_s=4.25,
    )
    assert value == pytest.approx((0.5131673057170362 + 0.5377030755083275) / 2)
    assert 0.25 <= value <= 1.25


def test_missing_public_envelope_keeps_neutral_factor():
    assert measured_ventilation_factor(
        diameter_m=0.002,
        release_g_s=80.0,
        wind_mode="unknown",
        wind_speed_m_s=3.0,
    ) == pytest.approx(1.0)


def test_virtual_detector_uses_public_factor_only_when_release_inputs_exist():
    safety = VirtualSafetyRuntime()
    safety.wind_direction_deg = 90.0  # storage axis -> co-flow
    safety.wind_speed_m_s = 3.5
    base = safety.detector_multiplier("cascade.medium")
    calibrated = safety.detector_multiplier(
        "cascade.medium", mass_flow_g_s=5.0, leak_diameter_m=0.001
    )
    assert calibrated == pytest.approx(base * 0.5131673057170362)
    assert safety.detector_multiplier("cascade.medium") == pytest.approx(base)
