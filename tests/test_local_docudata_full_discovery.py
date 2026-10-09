import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "research/local_docudata_full_discovery_2026_10_09.json"


def test_full_local_discovery_is_large_but_not_a_full_loop_claim():
    record = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    broad = record["broad_scan"]
    refined = record["refined_header_screen"]
    assert broad["machine_readable_files_screened"] == 38_528
    assert broad["csv_tsv_headers_screened"] == 12_804
    assert refined["vehicle_pressure_temperature_flow_time_candidates"] == 0
    assert record["eligibility"]["eligible_synchronized_station_dispenser_vehicle_cohort"] == 0
    assert record["eligibility"]["runtime_parameter_application"] is False


def test_full_local_discovery_privacy_boundary_is_closed():
    privacy = json.loads(ARTIFACT.read_text(encoding="utf-8"))["privacy"]
    assert all(value is False for value in privacy.values())
