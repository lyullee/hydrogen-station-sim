from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "research/usn_ignited_jet_dataset_recheck_2026_10_11.json"


def test_usn_dataset_is_staged_as_public_component_data_only():
    record = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    assert record["status"] == "PUBLIC_RAW_COMPONENT_DATASET_POST_ACCESS_DIAGNOSTIC_ONLY"
    assert record["source"]["license"] == "CC0 1.0"
    assert record["source"]["dataset_doi"] == "10.18710/X044QK"
    assert record["access_audit"]["file_count"] == 47
    assert record["access_audit"]["raw_csv_count"] == 39
    assert record["access_audit"]["raw_csv_files_downloaded"] is False
    assert record["access_audit"]["raw_csv_file_accessed"] is True
    assert record["access_audit"]["raw_csv_outcomes_opened_before_protocol"] is True
    assert record["access_audit"]["streamed_diagnostic"]["rows_read"] == 5000004
    assert record["eligibility"]["public_raw_component_consequence_data"] is True
    assert record["eligibility"]["hrs_dispenser_validation"] is False
    assert record["eligibility"]["station_to_vehicle_full_loop_validation"] is False
    assert record["eligibility"]["current_runtime_validation_status"] == "NOT_REPLAYED"
    assert "no case-specific fitting" in record["replay_protocol_requirement"]["parameter_policy"]
    assert record["claim_boundary"]
