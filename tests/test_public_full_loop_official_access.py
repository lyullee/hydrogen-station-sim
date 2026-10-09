from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_official_access_check_keeps_public_full_loop_boundary_explicit() -> None:
    path = ROOT / "research/public_full_loop_official_source_access_check_2026_10_09.json"
    record = json.loads(path.read_text(encoding="utf-8"))
    assert record["status"] == "NO_PUBLIC_RAW_STATION_TO_VEHICLE_TRACE_CONFIRMED"
    assert record["aggregate"]["source_count"] == 8
    assert record["aggregate"]["eligible_full_loop_source_count"] == 0
    assert record["aggregate"]["official_station_to_vehicle_raw_trace_confirmed"] is False
    assert record["decision"]["smallest_next_request"] == "tier_1_component_pilot"
    assert all(item["full_loop_eligible"] is False for item in record["sources"])
    rendered = path.read_text(encoding="utf-8")
    assert "company" not in rendered.lower()
    assert "manufacturer" not in rendered.lower()
