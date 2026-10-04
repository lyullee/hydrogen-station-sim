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
    by_id = {item["id"]: item for item in record["sources_checked"]}
    assert by_id["h2stations_api"]["thermodynamic_fill_trace"] is False
    assert by_id["nrel_h2iq_2024"]["thermodynamic_fill_trace"] is False
    assert by_id["nrel_hdtada_repository"]["classification"] == "SOFTWARE_ONLY"
    assert len(by_id["nrel_hdtada_repository"]["file_inventory"]) == 3
    assert by_id["nlr_data_catalog_2026_10_04"]["catalog_pages_inspected"] == 5
    assert by_id["enda_h2_mobility_monitoring"]["classification"] == "CONTROLLED_DATA_REQUEST_LEAD"
    assert "synchronized" in by_id["zbt_methytrucks_2026_sampling_intercomparison"]["supplementary_contents"]
