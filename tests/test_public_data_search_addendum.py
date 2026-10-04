import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_public_data_addendum_keeps_full_loop_gate_open():
    record = json.loads(
        (
            ROOT
            / "research/public_data_search_addendum_2026_10_04.json"
        ).read_text(encoding="utf-8")
    )
    assert record["decision"] == "NO_NEW_ELIGIBLE_PUBLIC_RAW_SET"
    assert record["gate_impact"] == "independent_full_loop_gate_remains_open"
    assert len(record["sources_checked"]) >= 5
    assert any(
        item["id"] == "oh_kgs_2025" and item["public_synchronized_raw_logger"] is False
        for item in record["sources_checked"]
    )
    assert all(
        item["classification"] != "FULL_LOOP_HOLDOUT"
        for item in record["sources_checked"]
    )
