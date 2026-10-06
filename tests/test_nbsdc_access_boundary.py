import json
from pathlib import Path


def test_nbsdc_candidate_remains_access_limited_and_unscored():
    root = Path(__file__).resolve().parents[1]
    record = json.loads(
        (root / "research/nbsdc_heavy_vehicle_fast_refueling_access_recheck_2026_10_06.json")
        .read_text(encoding="utf-8")
    )
    access = record["access_boundary"]
    decision = record["validation_decision"]
    assert access["numeric_data_download_without_login"] is False
    assert access["raw_files_obtained"] is False
    assert access["raw_rows_written_to_repository"] is False
    assert decision["full_loop_external_holdout_eligible"] is False
    assert decision["component_or_protocol_candidate"] is True
    assert "claim" in decision["claim_boundary"].lower()
