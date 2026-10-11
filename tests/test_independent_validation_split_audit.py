import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "research/independent_validation_split_audit_2026_10_11.json"


def test_available_data_split_is_explicit_but_not_overclaimed():
    result = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    assert result["decision"]["existing_data_partitioned"] is True
    assert result["decision"]["station_to_vehicle_external_validation_created"] is False
    split = result["tables_method_split"]
    assert split["total_cases"] == 36
    assert split["calibration_case_count"] == 24
    assert split["within_source_holdout_case_count"] == 12
    assert len(split["calibration_cases"]) == 24
    assert len(split["within_source_holdout_cases"]) == 12
    assert result["mc_default_external_holdout"]["case_count"] == 8
    assert result["mc_default_external_holdout"]["screening_pass_count"] == 0
    assert result["full_loop_boundary"]["synchronized_station_to_vehicle_raw_bundle_count"] == 0


def test_public_station_to_vehicle_recheck_keeps_report_only_leads_out_of_scope():
    result = json.loads(
        (ROOT / "research/validation_data_split_and_scope_decision_2026_10_11.json")
        .read_text(encoding="utf-8")
    )
    search = result["station_to_vehicle_public_search"]
    assert search["status"] == "NO_ELIGIBLE_PUBLIC_SYNCHRONIZED_RAW_SET_IDENTIFIED"
    assert search["recheck_artifact"].endswith("external_full_loop_data_recheck_2026_10_11.json")
    leads = {item["id"]: item for item in search["reviewed_leads"]}
    assert leads["calstate_la_back_to_back"]["decision"] == "CUSTODIAN_REQUEST_ONLY"
    assert leads["h2_stations_europe_api_v2"]["decision"] == "STATION_REGISTRY_NOT_FULL_LOOP"
