from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_fch2rail_d61_boundary_is_hash_locked_and_context_only():
    record = json.loads(
        (ROOT / "research/fch2rail_d61_operating_range_boundary_2026_10_05.json")
        .read_text(encoding="utf-8")
    )
    assert record["source"]["pdf_sha256"] == (
        "d55d8d27096e8bcf9529f32a27beb797bff9634f5cfca9c53bdae6914ae27dd2c"
    )
    assert record["source"]["pdf_page_count"] == 41
    assert record["experiment"]["supply_boundary"] == (
        "300 bar tube-trailer storage, no chiller, 10 m hose"
    )
    assert record["experiment"]["average_flow_range_g_s"] == [11.54, 19.44]
    assert record["experiment"]["average_refuelling_speed_range_kg_min"] == [0.69, 1.17]
    assert record["eligibility"]["real_hrs_operating_range_context_eligible"] is True
    assert record["eligibility"]["synchronized_raw_full_loop_holdout_eligible"] is False
    assert record["eligibility"]["goal_completion_permitted"] is False
