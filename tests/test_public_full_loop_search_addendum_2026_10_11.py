from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "research/public_full_loop_search_addendum_2026_10_11.json"


def test_public_search_addendum_fails_closed_without_raw_full_loop_data() -> None:
    record = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    assert record["decision"] == "NO_NEW_ELIGIBLE_PUBLIC_RAW_FULL_LOOP_SET_IDENTIFIED"
    assert record["gate_impact"] == "full_loop_external_validation_remains_open"
    assert record["runtime_parameter_application"] is False
    assert record["prospective_holdout_eligible"] is False
    assert record["claim_supported"] is False
    assert len(record["screened_sources"]) == 4
    assert record["privacy"]["private_raw_rows_persisted"] is False
    assert record["privacy"]["local_source_paths_published"] is False

    rendered = json.dumps(record, ensure_ascii=False)
    assert "C:\\" not in rendered
    assert '"private_raw_rows_persisted": true' not in rendered
    assert all(source["decision"] for source in record["screened_sources"])
