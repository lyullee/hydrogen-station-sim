from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RECHECK = ROOT / "research/pressure_decay_public_access_recheck_2026_10_14.json"


def test_pressure_decay_recheck_keeps_unavailable_raw_data_fail_closed() -> None:
    payload = json.loads(RECHECK.read_text(encoding="utf-8"))
    assert len(payload["routes"]) == 2
    assert all(route["raw_pressure_time_found"] is False for route in payload["routes"])
    assert payload["runtime_parameter_changed"] is False
    assert payload["validation_gate_changed"] is False
