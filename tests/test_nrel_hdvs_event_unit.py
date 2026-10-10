from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_nrel_hdvs_parallel_tanks_are_one_event():
    record = json.loads(
        (ROOT / "research/nrel_hdvs_event_unit_audit_2026_10_11.json")
        .read_text(encoding="utf-8")
    )
    experiment = record["experiment"]
    assert experiment["independent_event_count"] == 1
    assert experiment["shared_clock_group_count"] == 1
    assert experiment["parallel_tank_channel_count"] == 7
    assert "not" in experiment["independence_rule"]

