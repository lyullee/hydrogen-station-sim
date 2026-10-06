import pytest
import json
from pathlib import Path

from h2station.ventilation_calibration import measured_ventilation_factor
from h2station.virtual_safety import VirtualSafetyRuntime

ROOT = Path(__file__).resolve().parents[1]


def test_public_measurement_factor_interpolates_and_is_bounded():
    value = measured_ventilation_factor(
        diameter_m=0.001,
        release_g_s=5.0,
        wind_mode="co-flow",
        wind_speed_m_s=4.25,
        statistic="median",
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
    assert calibrated == pytest.approx(base * 0.822490737992286)
    assert safety.detector_multiplier("cascade.medium") == pytest.approx(base)


def test_virtual_detector_can_select_median_for_sensitivity_comparison():
    safety = VirtualSafetyRuntime(empirical_ventilation_statistic="median")
    safety.wind_direction_deg = 90.0
    safety.wind_speed_m_s = 3.5
    base = safety.detector_multiplier("cascade.medium")
    assert safety.detector_multiplier(
        "cascade.medium", mass_flow_g_s=5.0, leak_diameter_m=0.001
    ) == pytest.approx(base * 0.5131673057170362)


def test_virtual_detector_rejects_unknown_empirical_statistic():
    with pytest.raises(ValueError, match="empirical_ventilation_statistic"):
        VirtualSafetyRuntime(empirical_ventilation_statistic="p90")


def test_public_envelope_records_spatial_upper_factor_without_raw_rows():
    record = json.loads(
        (ROOT / "research/grune_ventilation_empirical_envelope_2026_10_06.json")
        .read_text(encoding="utf-8")
    )
    assert record["definition"]["upper_envelope"]
    assert record["source"]["raw_rows_committed"] is False
    assert len(record["factors"]) == 42
    assert all(
        item["relative_factor_upper"] >= item["relative_factor"]
        for item in record["factors"]
    )
