import numpy as np
import pytest

from h2station.ignited_pressure_peaking import (
    simulate_ignited_pressure_peaking,
    vent_area_m2,
)


def _constant_release(vent_count: int):
    time_s = np.arange(0.0, 12.002, 0.002)
    flow_g_s = np.where((time_s >= 2.0) & (time_s <= 10.0), 6.6, 0.0)
    output_s = np.arange(0.0, 12.001, 0.01)
    return simulate_ignited_pressure_peaking(
        time_s,
        flow_g_s,
        initial_temperature_k=282.0,
        vent_area_m2_value=vent_area_m2(vent_count),
        output_time_s=output_s,
    )


def test_zero_release_preserves_ambient_pressure_and_temperature():
    time_s = np.arange(0.0, 3.002, 0.002)
    result = simulate_ignited_pressure_peaking(
        time_s,
        np.zeros_like(time_s),
        initial_temperature_k=285.0,
        vent_area_m2_value=vent_area_m2(1),
        output_time_s=np.arange(0.0, 3.001, 0.01),
    )
    assert np.max(np.abs(result.gauge_overpressure_kpa)) < 1.0e-9
    assert np.max(np.abs(result.enclosure_temperature_k - 285.0)) < 1.0e-9


def test_larger_passive_vent_reduces_ignited_pressure_peak():
    one_vent = _constant_release(1)
    two_vents = _constant_release(2)
    three_vents = _constant_release(3)
    assert one_vent.peak_overpressure_kpa > two_vents.peak_overpressure_kpa
    assert two_vents.peak_overpressure_kpa > three_vents.peak_overpressure_kpa
    assert one_vent.peak_overpressure_kpa > 20.0
    assert three_vents.peak_overpressure_kpa > 5.0


def test_invalid_vent_count_is_rejected():
    with pytest.raises(ValueError, match="1, 2, or 3"):
        vent_area_m2(4)
