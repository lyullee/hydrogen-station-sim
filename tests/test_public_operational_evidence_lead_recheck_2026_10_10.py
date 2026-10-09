from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "research/public_operational_evidence_lead_recheck_2026_10_10.json"


def test_public_operational_leads_remain_claim_bounded() -> None:
    record = json.loads(ARTIFACT.read_text(encoding="utf-8"))

    assert record["decision"] == "NO_NEW_ELIGIBLE_PUBLIC_RAW_FULL_LOOP_SET_IDENTIFIED"
    assert len(record["sources"]) == 2
    assert record["minimum_full_loop_input"]["event_count"] == 3
    assert all(item["raw_synchronized_archive_located"] is False for item in record["sources"])
    rendered = json.dumps(record, ensure_ascii=False)
    assert "C:\\" not in rendered
    assert all("rows" not in item for item in record["sources"])
    assert record["privacy"]["private_raw_rows_persisted"] is False
