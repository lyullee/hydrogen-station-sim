import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_full_loop_request_package_is_explicit_and_non_claiming():
    path = ROOT / "research/full_loop_raw_data_request_package_2026_10_05.json"
    record = json.loads(path.read_text(encoding="utf-8"))
    assert record["status"] == "REQUEST_SPECIFICATION_ONLY"
    assert len(record["minimum_channels"]) >= 10
    assert len(record["custodian_routes"]) >= 6
    assert record["evaluation_guard"]["freeze_before_outcome_access"] is True
    assert record["evaluation_guard"]["post_freeze_parameter_tuning"] is False
    assert record["evaluation_guard"]["goal_completion_permitted"] is False
    assert "not evidence" in record["claim_boundary"].lower()
    component = record["minimum_useful_component_bundle"]
    assert component["minimum_event_count"] == 3
    assert len(component["required_channels"]) == 5
    assert "full_station_to_vehicle_holdout_claim" in component["not_allowed"]


def test_request_markdown_mentions_hashes_and_holdout_freeze():
    text = (
        ROOT / "research/FULL_LOOP_RAW_DATA_REQUEST_PACKAGE_2026_10_05.md"
    ).read_text(encoding="utf-8")
    assert "file hashes" in text
    assert "Before opening numerical outcomes, freeze" in text
    assert "change the current gate status" in text
    assert "minimum useful component bundle" in text
    assert "three-event" in text
    assert "export_confidential_component_bundle.py" in text
    assert "H2STATION_COMPONENT_BUNDLE_RECEIPT" in text
