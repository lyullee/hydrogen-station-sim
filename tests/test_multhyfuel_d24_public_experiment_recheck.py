from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_multhyfuel_public_dispenser_experiment_is_traceable_but_not_full_loop():
    report = json.loads(
        (ROOT / "research/multhyfuel_d24_public_experiment_recheck_2026_10_05.json").read_text(
            encoding="utf-8"
        )
    )
    assert report["status"] == "PUBLIC_MULTHYFUEL_D24_EXPERIMENT_RECHECKED"
    assert report["download"]["http_status"] == 200
    assert report["download"]["sha256_matches_expected"] is True
    assert report["download"]["pdf_pages"] >= 25
    assert all(report["page_anchors"].values())
    assert report["eligibility_decision"]["consequence_benchmark_eligible"] is True
    assert report["eligibility_decision"]["full_loop_station_vehicle_holdout_eligible"] is False
    assert report["eligibility_decision"]["saga_effectiveness_eligible"] is False
    assert report["reported_measurements"]["jetfire_700bar_measured_flow_g_s"] == 40.0
    assert report["reported_measurements"]["internal_700bar_0_2mm_flow_g_s"] == 9.0
    assert report["claim_boundary"]
