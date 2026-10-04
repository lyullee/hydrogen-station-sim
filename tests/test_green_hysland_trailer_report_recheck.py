from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_green_hysland_report_is_component_context_only():
    report = json.loads(
        (ROOT / "research/green_hysland_trailer_report_recheck_2026_10_05.json").read_text(
            encoding="utf-8"
        )
    )
    assert report["status"] == "PUBLIC_GREENHYSLAND_REPORT_RECHECKED"
    assert report["download"]["http_status"] == 200
    assert len(report["download"]["sha256"]) == 64
    assert report["download"]["pdf_pages"] >= 1
    assert report["tube_trailer_context"]["all_required_rows_present"] is True
    assert report["eligibility_decision"]["component_boundary_context_eligible"] is True
    assert report["eligibility_decision"]["full_loop_external_holdout_eligible"] is False
    assert report["hrs_provisional_boundary"]["populated_transaction_values"] is False
    assert report["claim_boundary"]
