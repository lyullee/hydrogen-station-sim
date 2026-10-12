from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RECHECK = ROOT / "research/kit_lh2_download_recheck_2026_10_12.json"


def test_kit_recheck_records_range_access_without_promoting_partial_archive() -> None:
    payload = json.loads(RECHECK.read_text(encoding="utf-8"))
    source = payload["source"]
    recheck = payload["recheck"]
    local = payload["local_partial_archive"]
    eligibility = payload["eligibility"]

    assert recheck["session_range_probe"] == "PASS"
    assert recheck["sparse_resume_probe"]["status"] == "PASS"
    assert recheck["sparse_resume_probe"]["signal_values_opened"] is False
    assert recheck["full_resume_attempt"]["status"] == "RATE_LIMITED_HTTP_429"
    assert recheck["full_resume_attempt"]["bytes_added_to_archive"] == 0
    assert local["bytes"] < source["publisher_reported_bytes"]
    assert local["matches_publisher_md5"] is False
    assert eligibility["stage1_integrity_verified"] is False
    assert eligibility["stage1_inventory_complete"] is False
    assert eligibility["stage2_eligible"] is False
    assert eligibility["promoted_to_validation"] is False
