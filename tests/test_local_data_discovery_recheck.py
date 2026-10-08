"""Regression checks for the privacy-bounded local data recheck."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "research/local_hydrogen_station_data_discovery_recheck_2026_10_09.json"


def test_local_recheck_is_privacy_bounded() -> None:
    record = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    privacy = record["privacy"]
    assert all(value is False for value in privacy.values())


def test_local_recheck_separates_measured_and_derived_data() -> None:
    record = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    groups = {item["id"]: item for item in record["candidate_groups"]}

    measured = groups["confidential_station_measurement_bundle"]
    assert measured["file_count"] == 33
    assert measured["deduplicated_rows"] == 56_854_143
    assert measured["attested_roles"]["vehicle_side_channels_attested"] == 0

    derived = groups["derived_simulator_telemetry_exports"]
    assert derived["independence"] == "not_independent_measured_data"
    assert derived["ineligible_use"]
    assert record["coverage_assessment"][
        "derived_exports_must_be_excluded_from_external_validation"
    ] is True


def test_local_recheck_preserves_full_loop_boundary() -> None:
    coverage = json.loads(ARTIFACT.read_text(encoding="utf-8"))["coverage_assessment"]
    assert coverage["local_station_data_is_sparse"] is False
    assert coverage["station_side_dynamic_evidence_is_substantial"] is True
    assert coverage["vehicle_side_full_loop_validation_ready"] is False
    assert coverage["quantitative_consequence_validation_ready"] is False
