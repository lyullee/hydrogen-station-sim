from __future__ import annotations

import json

from h2station.calibration_profiles import load_measured_boundary_calibration


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
