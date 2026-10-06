from __future__ import annotations

from scripts.recheck_confidential_operational_profile import compare_aggregate

from pathlib import Path
import json


ROOT = Path(__file__).resolve().parents[1]


def _fresh() -> dict:
    return {
        "files_read": 2,
        "sampled_rows": 10,
        "duration_s": 90.0,
        "median_sample_period_s": 10.0,
        "maximum_gap_s": 11.0,
        "boundary_pressure_pa": {
            "min": 50_000_000.0,
            "median": 60_000_000.0,
            "max": 70_000_000.0,
            "noise_sigma": 1000.0,
            "positive_ramp_p95": 2000.0,
        },
        "recharge_hysteresis_pa": 500_000.0,
        "recharge_restart_margin_pa": 500_000.0,
        "channel_roles": ["station_pressure"],
    }


def test_recheck_compares_attested_core_and_omits_unmapped_channels():
    fresh = _fresh()
    result = compare_aggregate(fresh, {"calibration": fresh})
    assert result["matches"] is True
    assert "sampled_rows" in result["fields_compared"]
    assert "state_transition_count" in result["fields_omitted_without_attestation"]
    assert "boundary_temperature_degC.max" in result["fields_omitted_without_attestation"]
    assert result["mismatches"] == []


def test_recheck_detects_drift_without_overwriting_profile():
    fresh = _fresh()
    expected = {"calibration": {**fresh, "recharge_restart_margin_pa": 600_000.0}}
    result = compare_aggregate(fresh, expected)
    assert result["matches"] is False
    assert result["mismatches"] == [{
        "field": "recharge_restart_margin_pa",
        "fresh": 500_000.0,
        "expected": 600_000.0,
    }]


def test_committed_private_recheck_is_a_match_and_keeps_scope_boundary():
    record = json.loads(
        (
            ROOT
            / "research/confidential_operational_profile_recheck_2026_10_06.json"
        ).read_text(encoding="utf-8")
    )
    assert record["committed_profile_comparison"]["matches"] is True
    assert record["runtime_decision"]["committed_profile_replaced"] is False
    assert record["runtime_decision"]["measured_boundary_calibration_remains_opt_in"] is True
    assert record["source_paths_published"] is False
    assert record["raw_rows_persisted"] is False
    assert record["fresh_calibration"]["sampled_rows"] == 10896
