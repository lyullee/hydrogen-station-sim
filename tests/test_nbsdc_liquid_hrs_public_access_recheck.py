import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RECHECK = ROOT / "research" / "nbsdc_liquid_hrs_public_access_recheck_2026_10_05.json"
PROTOCOL = ROOT / "research" / "nbsdc_liquid_hrs_intake_protocol_2026_10_05.json"


def test_nbsdc_liquid_hrs_recheck_preserves_application_boundary():
    record = json.loads(RECHECK.read_text(encoding="utf-8"))
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    assert record["status"] == "REAL_LHRS_ACCESS_BOUNDARY_NO_RAW_NUMERICAL_HOLDOUT"
    assert record["source"]["data_id"] == protocol["source"]["data_id"]
    assert record["source"]["share_range"] == "完全共享"
    assert record["metadata_observation"]["file_count"] == 7
    assert len(record["public_file_inventory"]) == 7
    assert record["description_file"]["downloaded"] is True
    assert record["raw_download_probes"]["portal_body_code"] == 403
    assert record["raw_download_probes"]["raw_numerical_files_obtained"] is False
    assert record["eligibility"]["full_loop_holdout_eligible"] is False
    assert "not numerical validation" in record["claim_boundary"]
