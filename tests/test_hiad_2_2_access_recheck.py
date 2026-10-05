import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_hiad_2_2_station_incident_inventory_is_provenance_only():
    record = json.loads(
        (ROOT / "research/hiad_2_2_access_recheck_2026_10_05.json").read_text(
            encoding="utf-8"
        )
    )
    assert record["status"] == "completed_public_accident_dataset_provenance_recheck"
    assert record["source"]["version"] == "HIAD 2.2"
    assert record["source"]["sha256"]
    assert record["workbook_observation"]["hydrogen_refuelling_station_records"] == 34
    assert len(record["station_case_index"]) == 34
    boundary = record["claim_boundary"].lower()
    assert "does not provide synchronized" in boundary
    assert "does not close" in boundary
