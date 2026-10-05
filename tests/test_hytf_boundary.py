from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_hytf_public_trace_is_pinned_and_component_only():
    record = json.loads(
        (ROOT / "research/hytf_open_tank_trace_boundary_2026_10_05.json")
        .read_text(encoding="utf-8")
    )
    assert record["source"]["repository_commit"] == "4482486fa9ab02360af364f3d1dad5ea48eabaf8"
    assert record["source"]["dataset_sha256"] == "3f11f75afec75e71fa18893e0a351966467a436f569e8349065e06c1649673a0"
    assert record["experiment"]["sample_count"] == 2536
    assert record["experiment"]["channels"]["tank_thermocouples"]
    assert record["access_observation"]["raw_machine_readable_trace_retrieved"] is True
    assert record["access_observation"]["mass_flow_or_transferred_mass_trace"] is False
    assert record["eligibility"]["component_tank_screen_eligible_after_protocol_freeze"] is True
    assert record["eligibility"]["full_loop_external_holdout_eligible"] is False
    assert record["eligibility"]["goal_completion_permitted"] is False


def test_hytf_catalog_points_to_boundary_record():
    catalog = json.loads((ROOT / "research/data_sources.json").read_text(encoding="utf-8"))
    source = catalog["sources"]["hytf_190821_public_tank_trace"]
    assert source["boundary_record"].endswith(
        "hytf_open_tank_trace_boundary_2026_10_05.json"
    )
    assert source["sha256"]
