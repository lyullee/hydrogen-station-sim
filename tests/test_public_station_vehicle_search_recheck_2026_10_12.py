from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "research/public_station_vehicle_search_recheck_2026_10_12.json"


def test_latest_station_vehicle_search_is_a_privacy_safe_negative_boundary():
    record = json.loads(ARTIFACT.read_text(encoding="utf-8"))

    assert record["artifact_type"] == "station_to_vehicle_public_search_recheck"
    assert record["recorded_at"] == "2026-10-12"
    assert record["decision"] == (
        "NO_NEW_ELIGIBLE_PUBLIC_RAW_STATION_TO_VEHICLE_SET_IDENTIFIED"
    )
    assert record["primary_goal_impact"]["full_loop_external_validation"] == (
        "OUT_OF_SCOPE"
    )
    assert "common clock" in record["primary_goal_impact"]["reentry_condition"]
    assert len(record["sources"]) == 11
    assert all(
        set(source).issubset({"name", "doi", "url", "observed_role", "decision", "reason"})
        for source in record["sources"]
    )

    rendered = json.dumps(record, ensure_ascii=False)
    assert "C:\\" not in rendered
    assert "raw_rows" not in rendered
    assert "source_path" not in rendered
