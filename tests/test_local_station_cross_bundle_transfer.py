"""Regression checks for the privacy-bounded station transfer diagnostic."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT / "research/local_station_cross_bundle_transfer_result_2026_10_09.json"
PROTOCOL = ROOT / "research/local_station_cross_bundle_transfer_protocol_2026_10_09.json"


def test_cross_bundle_transfer_artifact_is_privacy_bounded() -> None:
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    assert result["artifact_type"] == "local_station_cross_bundle_pressure_transfer_diagnostic"
    for key in (
        "source_identifiers_published",
        "source_paths_published",
        "source_filenames_published",
        "source_headers_published",
        "raw_rows_persisted",
        "absolute_timestamps_published",
        "calendar_dates_published",
    ):
        assert result[key] is False
    assert result["decision"]["independent_external_validation"] is False
    assert result["decision"]["full_loop_vehicle_validation"] is False
    assert result["decision"]["runtime_parameter_application"] is False
    assert result["decision"]["fixed_candidate_corroborated_on_transfer_bundle"] is True


def test_cross_bundle_protocol_freezes_unit_normalization_and_claim_boundary() -> None:
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    assert protocol["status"] == "protocol_frozen_before_cross_bundle_outcome_access"
    assert protocol["method"]["pressure_normalization"].startswith("owner-attested")
    assert protocol["method"]["candidate_not_fit_to_transfer_bundle"] is True
    assert protocol["decision_boundary"]["independent_external_validation"] is False
    assert protocol["decision_boundary"]["full_loop_vehicle_validation"] is False
    assert "does not validate vehicle filling" in protocol["claim_boundary"]
