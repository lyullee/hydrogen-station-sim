from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_local_schema_inventory_is_privacy_bounded_and_does_not_promote_full_loop():
    record = json.loads(
        (ROOT / "research/local_full_loop_schema_inventory_2026_10_11.json")
        .read_text(encoding="utf-8")
    )

    counts = record["candidate_schema_counts"]
    assert counts["full_loop_candidate"] == 0
    assert counts["station_recharge_candidate"] == 0
    assert counts["vehicle_fill_candidate"] == 0
    privacy = record["privacy_boundary"]
    assert all(value is False for value in privacy.values())
    assert record["source_label"] == "authorized-private-hrs-roots-and-controlled-export"
