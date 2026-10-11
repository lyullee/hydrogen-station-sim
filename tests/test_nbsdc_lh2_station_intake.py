from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _load(name: str) -> dict:
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def test_nbsdc_protocol_is_frozen_and_numerical_access_boundary_is_explicit():
    protocol_path = ROOT / "research/nbsdc_lh2_station_intake_protocol_2026_10_12.json"
    protocol = _load("research/nbsdc_lh2_station_intake_protocol_2026_10_12.json")
    result = _load("research/nbsdc_lh2_station_intake_result_2026_10_12.json")

    assert protocol["status"] == "frozen_before_numerical_access"
    assert protocol["evaluation"]["numerical_outcomes_accessed_before_freeze"] is False
    assert result["protocol_sha256"] == hashlib.sha256(protocol_path.read_bytes()).hexdigest()
    assert result["status"] == "metadata_accessed_numerical_files_access_denied"
    assert result["aggregate"] == {
        "file_count": 7,
        "downloaded_count": 1,
        "access_denied_count": 6,
        "all_files_downloaded": False,
        "catalogue_byte_mismatch_count": 0,
        "raw_rows_persisted": False,
        "runtime_parameter_changed": False,
        "claim_supported": False,
    }
    assert len(result["files"]) == 7
    assert sum(item["access_status"] == "access_denied" for item in result["files"]) == 6
    assert all(item["raw_rows_persisted_in_result"] is False for item in result["files"])
    assert "source_paths_published" not in str(result)


def test_nbsdc_intake_does_not_create_a_station_to_vehicle_claim():
    result = _load("research/nbsdc_lh2_station_intake_result_2026_10_12.json")
    boundary = result["claim_boundary"]
    assert result["aggregate"]["claim_supported"] is False
    assert result["aggregate"]["runtime_parameter_changed"] is False
    assert "full-loop" in boundary
    assert "vehicle" in boundary
