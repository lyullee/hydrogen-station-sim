from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "research/public_full_loop_search_recheck_2026_10_11.json"


def test_2026_10_11_public_recheck_is_privacy_safe_and_does_not_open_full_loop_gate():
    record = json.loads(ARTIFACT.read_text(encoding="utf-8"))

    assert record["decision"] == "NO_NEW_ELIGIBLE_PUBLIC_RAW_FULL_LOOP_SET_IDENTIFIED"
    assert record["gate_impact"] == "full_loop_external_validation_remains_open"
    assert record["prospective_holdout_eligible"] is False
    assert record["runtime_parameter_application"] is False
    assert record["claim_supported"] is False
    assert len(record["screened_sources"]) == 4
    assert record["privacy"]["private_raw_rows_persisted"] is False
    assert record["privacy"]["local_source_paths_published"] is False
    assert record["minimum_next_input"]["event_count"] == 3

    rendered = json.dumps(record, ensure_ascii=False)
    assert "C:\\" not in rendered
    assert "rows" not in record["privacy"]
    assert all("rows" not in source for source in record["screened_sources"])

    api = next(item for item in record["screened_sources"] if item["id"] == "h2_stations_eu_api_v2")
    assert api["decision"] == "INVENTORY_AND_STATUS_CONTEXT_ONLY"
    assert api["vehicle_pressure_temperature_channels"] is False

    h2protocol = next(item for item in record["screened_sources"] if item["id"] == "h2protocol_j2601_raw_lab_route")
    assert h2protocol["raw_synchronized_archive_located"] is True
    assert h2protocol["station_controller_or_esd_channels"] is False
    assert h2protocol["decision"] == "COMPONENT_BOUNDARY_ONLY"
