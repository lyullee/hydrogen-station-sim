import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_kgs_real_station_lead_records_access_boundary_without_promoting_holdout():
    record = json.loads(
        (ROOT / "research/kgs_hrs_code_access_recheck_2026_10_05.json")
        .read_text(encoding="utf-8")
    )
    assert record["source"]["published_doi"] == "10.1007/s11814-025-00551-9"
    assert record["source"]["reported_real_hrs_scenarios"] == 6
    assert record["anonymous_access_check"]["result"] == "REDIRECTED_TO_SIGN_IN"
    assert record["anonymous_access_check"]["files_retrieved"] == 0
    assert record["classification"]["real_station_provenance"] is True
    assert record["classification"]["public_raw_logger_available"] is False
    assert record["classification"]["full_loop_station_vehicle_holdout_eligible"] is False
    assert record["classification"]["goal_completion_permitted"] is False
    assert len(record["minimum_requested_package"]) >= 7
