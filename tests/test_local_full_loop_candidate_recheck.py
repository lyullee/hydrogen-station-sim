import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_local_full_loop_recheck_is_privacy_bounded_and_does_not_overclaim():
    record = json.loads(
        (ROOT / "research/local_full_loop_candidate_recheck_2026_10_09.json")
        .read_text(encoding="utf-8")
    )

    privacy = record["privacy"]
    assert all(value is False for value in privacy.values())
    measured = next(item for item in record["candidate_classes"] if item["id"] == "measured_station_bundle")
    assert measured["file_count"] == 33
    assert measured["deduplicated_rows"] == 56854143
    assert measured["vehicle_side_semantics_attested"] is False
    assert record["coverage_assessment"]["local_hydrogen_station_data_is_sparse"] is False
    assert record["coverage_assessment"]["new_local_full_loop_cohort_found"] is False
    assert record["coverage_assessment"]["full_loop_holdout_eligible"] is False
    assert record["decision"] == "NO_NEW_LOCAL_FULL_LOOP_COHORT"

    simulator = next(item for item in record["candidate_classes"] if item["id"] == "derived_simulator_exports")
    assert simulator["independent_measured_data"] is False
    assert simulator["decision"] == "SIMULATOR_REGRESSION_ONLY"

    broad_scan = next(item for item in record["candidate_classes"] if item["id"] == "broad_regex_candidate_manifest")
    assert broad_scan["semantic_attestation"] is False
    assert broad_scan["decision"] == "NOT_ELIGIBLE_UNTIL_HEADER_UNIT_ATTESTATION"
