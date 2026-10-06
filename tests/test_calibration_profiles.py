from __future__ import annotations

import json

import pytest

from h2station.calibration_profiles import (
    load_bank_pressure_envelopes,
    load_measured_boundary_calibration,
)


def test_sanitized_measured_boundary_profile_is_bounded(tmp_path):
    source = {
        "artifact_type": "confidential_station_boundary_calibration_summary",
        "source_identifiers_published": False,
        "raw_rows_persisted": False,
        "exact_source_dates_published": False,
        "sampled_rows": 10,
        "recommended_recharge_hysteresis_pa": 250000.0,
        "recommended_recharge_restart_margin_pa": 250000.0,
        "eligibility": {
            "station_boundary_calibration_supported": True,
            "full_station_vehicle_validation": False,
        },
        "source_scope": "owner-controlled station boundary",
        "claim_boundary": "station-boundary calibration only",
    }
    path = tmp_path / "profile.json"
    path.write_text(json.dumps(source), encoding="utf-8")
    profile = load_measured_boundary_calibration(path)
    assert profile is not None
    assert profile.recharge_hysteresis_pa == 250000.0
    assert profile.evidence_artifact.endswith("profile.json")


def test_unsafe_profile_is_disabled(tmp_path):
    path = tmp_path / "profile.json"
    path.write_text(json.dumps({"artifact_type": "wrong"}), encoding="utf-8")
    assert load_measured_boundary_calibration(path) is None


def test_operational_envelope_requires_pressure_semantics_attestation(tmp_path):
    source = {
        "artifact_type": "confidential_operational_envelope_calibration_summary",
        "source_identifiers_published": False,
        "raw_rows_persisted": False,
        "exact_source_dates_published": False,
        "sampled_rows": 10,
        "recommended_recharge_hysteresis_pa": 250000.0,
        "recommended_recharge_restart_margin_pa": 250000.0,
        "eligibility": {
            "station_boundary_calibration_supported": True,
            "full_station_vehicle_validation": False,
        },
        "channel_attestation": {
            "pressure_boundary_semantics_attested": False,
        },
    }
    path = tmp_path / "unattested-operational-profile.json"
    path.write_text(json.dumps(source), encoding="utf-8")
    assert load_measured_boundary_calibration(path) is None


def test_quality_warnings_disable_profile_application(tmp_path):
    source = {
        "artifact_type": "confidential_station_boundary_calibration_summary",
        "source_identifiers_published": False,
        "raw_rows_persisted": False,
        "exact_source_dates_published": False,
        "sampled_rows": 100,
        "median_sample_period_s": 60.0,
        "maximum_gap_s": 3600.0,
        "quality_warnings": ["nonpositive_pressure_excluded"],
        "recommended_recharge_hysteresis_pa": 500000.0,
        "recommended_recharge_restart_margin_pa": 500000.0,
        "eligibility": {
            "station_boundary_calibration_supported": True,
            "full_station_vehicle_validation": False,
        },
    }
    path = tmp_path / "suspect-profile.json"
    path.write_text(json.dumps(source), encoding="utf-8")
    assert load_measured_boundary_calibration(path) is None


def test_sparse_profile_is_not_applied_even_without_explicit_warning(tmp_path):
    source = {
        "artifact_type": "confidential_station_boundary_calibration_summary",
        "source_identifiers_published": False,
        "raw_rows_persisted": False,
        "exact_source_dates_published": False,
        "sampled_rows": 100,
        "median_sample_period_s": 120.0,
        "maximum_gap_s": 2000.0,
        "quality_warnings": [],
        "recommended_recharge_hysteresis_pa": 500000.0,
        "recommended_recharge_restart_margin_pa": 500000.0,
        "eligibility": {
            "station_boundary_calibration_supported": True,
            "full_station_vehicle_validation": False,
        },
    }
    path = tmp_path / "sparse-profile.json"
    path.write_text(json.dumps(source), encoding="utf-8")
    assert load_measured_boundary_calibration(path) is None


def test_default_profile_prefers_deidentified_operational_envelope():
    profile = load_measured_boundary_calibration()
    assert profile is not None
    assert profile.profile_id == "owner_measured_operational_envelope_v1"
    assert profile.sampled_rows == 10896
    assert profile.recharge_restart_margin_pa == 540000.0
    assert profile.evidence_artifact.endswith(
        "confidential_operational_envelope_calibration_summary_2026_10_06.json"
    )
    metadata = profile.runtime_metadata()
    assert metadata["observed_pressure_range_mpa"] == {
        "min_mpa": 56.295,
        "median_mpa": 62.5,
        "max_mpa": 63.36,
    }
    assert metadata["state_transition_count"] == 274
    assert metadata["channel_attestation"] == {
        "pressure_boundary_semantics_attested": True,
        "lifecycle_counter_semantics_attested": False,
        "temperature_boundary_role_attested": False,
        "mass_flow_units_attested": False,
    }


def test_pressure_envelope_comparison_is_scope_diagnostic_only():
    profile = load_measured_boundary_calibration()
    assert profile is not None
    inside = profile.pressure_envelope_comparison(60.0)
    assert inside["status"] == "within_measured_envelope"
    assert inside["margin_to_nearest_limit_mpa"] == pytest.approx(3.36)
    above = profile.pressure_envelope_comparison(65.0)
    assert above["status"] == "above_measured_envelope"
    assert above["outside_by_mpa"] == pytest.approx(1.64)
    unavailable = profile.pressure_envelope_comparison(None)
    assert unavailable["status"] == "unavailable"
    assert "안전 한계" in unavailable["claim_limit"]


def test_bank_pressure_envelope_is_diagnostic_and_uses_robust_quantiles():
    profile = load_bank_pressure_envelopes()
    assert profile is not None
    result = profile.compare({"medium": 42.0, "high": 90.0, "low": 20.0})
    assert result["runtime_parameter_application"] is False
    assert result["banks"]["medium"]["comparison"] == (
        "within_observed_robust_range"
    )
    assert result["banks"]["high"]["comparison"] == (
        "above_observed_robust_range"
    )
    assert "full-loop" in result["claim_boundary"]
