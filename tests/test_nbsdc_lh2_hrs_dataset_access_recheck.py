"""Integrity checks for the newly located NBSDC/Tongji HRS data lead."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT / "research/nbsdc_lh2_hrs_dataset_access_recheck_2026_10_05.json"
QUEUE = ROOT / "research/validation_data_request_dispatch_queue_2026_10_05.json"
HYFILL = ROOT / "research/hyfill_hd_hrs_data_lead_2026_10_05.json"


def test_nbsdc_record_preserves_access_boundary_and_candidate_scope() -> None:
    record = json.loads(RESULT.read_text(encoding="utf-8"))
    assert record["status"] == "ACCESS_RESTRICTED_RAW_CANDIDATE_RECHECKED"
    assert record["source"]["data_id"] == "67d50e37195d260905af9869"
    assert record["dataset_description_evidence"]["reported_time_resolution"] == "1 second"
    files = record["file_tree_observation"]["files"]
    assert len(files) == 7
    assert {item["name"] for item in files} >= {
        "35MPa加氢机1.xlsx",
        "35MPa加氢机2.xlsx",
        "70MPa加氢机.csv",
        "90MPa压缩机.xlsx",
        "液氢泵-液氢储罐.xlsx",
        "高压储氢瓶组.xlsx",
    }
    assert record["eligibility"]["candidate_for_full_loop_validation"] is True
    assert record["eligibility"]["current_eligible"] is False
    assert record["source"]["raw_file_download_response"]["application_code"] == 403


def test_nbsdc_data_request_is_queued_without_automatic_dispatch() -> None:
    queue = json.loads(QUEUE.read_text(encoding="utf-8"))
    assert queue["status"] == "NOT_SENT_GMAIL_NOT_CONNECTED"
    item = next(
        item for item in queue["queue"]
        if item["id"] == "nbsdc_tongji_lh2_hrs_operational_dataset"
    )
    assert item["status"] == "request_draft_ready_access_application_required"
    assert item["evidence"] == "research/nbsdc_lh2_hrs_dataset_access_recheck_2026_10_05.json"
    assert (ROOT / item["draft"]).is_file()


def test_hyfill_is_recorded_as_a_real_station_data_lead_only() -> None:
    record = json.loads(HYFILL.read_text(encoding="utf-8"))
    assert record["status"] == "REAL_HRS_DATA_REQUEST_LEAD_NO_RAW_ARCHIVE"
    assert record["reported_experiment"]["reported_test_count"] == ">50 refuelling and defuelling tests"
    assert record["access_boundary"]["raw_synchronized_logger_retrieved"] is False
    assert record["eligibility"]["candidate_for_full_loop_validation"] is True
    assert record["access_boundary"]["full_loop_holdout_eligible_now"] is False
    queue = json.loads(QUEUE.read_text(encoding="utf-8"))
    item = next(item for item in queue["queue"] if item["id"] == "hyfill_hd_hrs_experiments_2026")
    assert item["status"] == "request_draft_ready"
    assert (ROOT / item["draft"]).is_file()
