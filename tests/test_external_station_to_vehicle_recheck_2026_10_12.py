import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_latest_public_station_vehicle_recheck_is_fail_closed():
    record = json.loads(
        (ROOT / "research/external_station_to_vehicle_recheck_2026_10_12.json").read_text(
            encoding="utf-8"
        )
    )

    assert record["status"] == "NO_NEW_ELIGIBLE_PUBLIC_RAW_SET_IDENTIFIED"
    decision = record["decision"]
    assert decision["eligible_public_synchronized_station_to_vehicle_set_count"] == 0
    assert decision["full_loop_external_validation"] == "OUT_OF_SCOPE"
    assert decision["primary_gate_changed"] is False
    assert "reentry_condition" in decision

