import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_priority_packet_is_minimal_privacy_safe_and_not_marked_as_contacted():
    packet = json.loads(
        (ROOT / "research/priority_data_request_packet_2026_10_10.json")
        .read_text(encoding="utf-8")
    )
    assert packet["contact_sent"] is False
    assert packet["minimum_event_count"] == 3
    assert "elapsed_time_s" in packet["required_channels"]
    assert "vehicle_or_receptacle_pressure_temperature" in packet["preferred_channels"]
    assert packet["privacy"]["raw_rows_persisted"] is False
    assert packet["decision"]["full_loop_validation_supported"] is False
    assert (ROOT / "research/PRIORITY_DATA_REQUEST_PACKET_2026_10_10.md").is_file()
