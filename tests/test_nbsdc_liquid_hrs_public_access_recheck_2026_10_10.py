import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "research" / "nbsdc_liquid_hrs_public_access_recheck_2026_10_10.json"


def test_nbsdc_2026_recheck_records_real_scope_without_admitting_raw_data():
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    assert report["status"] == "REAL_LHRS_METADATA_CONFIRMED_NUMERICAL_FILES_APPLICATION_CONTROLLED"
    assert report["source"]["data_id"] == "67d50e37195d260905af9869"
    assert report["metadata_observation"]["file_count"] == 7
    assert len(report["metadata_observation"]["numerical_file_inventory"]) == 6
    assert report["access_probe"]["numeric_download_portal_code"] == 403
    assert report["access_probe"]["raw_numerical_files_obtained"] is False
    assert report["eligibility"]["full_loop_holdout_eligible"] is False
    assert report["eligibility"]["high_value_request_candidate"] is True
    assert report["privacy"]["raw_rows_persisted"] is False
