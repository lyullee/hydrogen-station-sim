from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_nrel_hdvs_boundary_is_explicit_and_non_overclaimed():
    record = json.loads(
        (ROOT / "research/nrel_hdvs_raw_trace_boundary_2026_10_05.json")
        .read_text(encoding="utf-8")
    )
    assert record["source"]["workbook_sha256"] == (
        "1a3fbe64a50c1c97266bfe0372998513ad3ccec5600fab7bc4b9fc68ad4d9d0c"
    )
    assert record["experiment"]["nonempty_timed_row_count"] == 351
    assert record["experiment"]["tank_ids"] == [1, 2, 3, 5, 7, 8, 9]
    assert record["boundary_check"]["workbook_present_and_hash_verified"] is True
    assert record["boundary_check"]["physical_measurement_trace"] is True
    assert record["boundary_check"]["station_controller_or_cascade_state_present"] is False
    assert record["boundary_check"]["full_loop_external_holdout_eligible"] is False
    assert record["eligibility"]["partial_station_to_tank_boundary_eligible"] is True
    assert record["eligibility"]["goal_completion_permitted"] is False
