import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_external_station_to_vehicle_recheck_is_explicitly_bounded():
    path = ROOT / "research/external_station_to_vehicle_recheck_2026_10_11.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["status"] == "NO_NEW_ELIGIBLE_PUBLIC_RAW_SET_IDENTIFIED"
    assert payload["primary_goal_decision"]["full_loop_external_validation"] == "OUT_OF_SCOPE"
    assert "does not claim" in payload["primary_goal_decision"]["paper_limitation"]
    assert len(payload["candidates"]) >= 3
    additions = {item["name"]: item for item in payload["current_search_recheck"]["additional_hits"]}
    assert additions["DLR FCH2RAIL railway refueling measurement paper"]["decision"] == "REPORT_SUMMARY_ONLY"
    assert additions["DTU Hydrogen-Fuelling-Station Modelica library"]["decision"] == "MODEL_REFERENCE_NOT_EXTERNAL_RAW"
