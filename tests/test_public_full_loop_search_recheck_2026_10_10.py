from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "research/public_full_loop_search_recheck_2026_10_10.json"


def test_public_full_loop_recheck_is_explicitly_claim_limited() -> None:
    record = json.loads(ARTIFACT.read_text(encoding="utf-8"))

    assert record["decision"] == "NO_NEW_ELIGIBLE_PUBLIC_RAW_FULL_LOOP_SET_IDENTIFIED"
    assert record["gate_impact"] == "full_loop_external_validation_remains_open"
    assert len(record["screened_sources"]) == 9
    assert record["minimum_next_input"]["event_count"] == 3
    rendered = json.dumps(record, ensure_ascii=False)
    assert "C:\\" not in rendered
    assert "source_paths_published" not in record
    assert all("rows" not in item for item in record["screened_sources"])
    assert all("local paths" not in item.get("claim_limit", "").lower()
               for item in record["screened_sources"])
    kuroki = next(
        item for item in record["screened_sources"]
        if item["id"] == "nlr_kuroki_2023_vehicle_tank_fueling_experiment"
    )
    assert kuroki["decision"] == "PUBLISHED_EXPERIMENT_DESCRIPTION_DATA_NOT_SHARED"
    additions = record["latest_search_additions"]
    assert additions["decision"].startswith("No new eligible raw full-loop")
    assert additions["privacy"]["private_raw_rows_persisted"] is False
    assert len(additions["new_public_leads"]) == 4
    assert all(
        item["raw_synchronized_archive_located"] is False
        for item in additions["new_public_leads"]
    )
