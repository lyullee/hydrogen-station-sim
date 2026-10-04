from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_cip_live_tables_are_integrity_checked_without_full_loop_promotion():
    report = json.loads(
        (ROOT / "research/cip_2020_live_download_recheck_2026_10_05.json").read_text(
            encoding="utf-8"
        )
    )
    assert report["status"] == "PUBLIC_ENDPOINT_TABLES_RECHECKED"
    assert report["source"]["doi"] == "10.19799/j.cnki.2095-4239.2020.0049"
    tables = report["tables"]
    assert [row["table"] for row in tables] == ["T1", "T2", "T3", "T4"]
    assert all(row["http_status"] == 200 for row in tables)
    assert all(row["sha256_matches_expected"] is True for row in tables)
    assert all(row["inspection"]["rows"] == 3 for row in tables)
    assert all(row["inspection"]["has_time_axis"] is False for row in tables)
    assert report["eligibility_decision"]["full_loop_external_holdout_eligible"] is False
