from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RECHECK = ROOT / "research/nbsdc_hrs_operational_dataset_recheck_2026_10_06.json"


def test_public_operational_dataset_is_recorded_without_overclaiming_access():
    record = json.loads(RECHECK.read_text(encoding="utf-8"))
    source = record["source"]
    access = record["access_result"]
    eligibility = record["eligibility"]

    assert record["status"] == "PUBLIC_METADATA_CANDIDATE_ACCESS_LIMITED"
    assert source["cstr"] == "16666.11.nbsdc.aI3fJrzX"
    assert source["title"] == "Hydrogen Refuelling Station Operational Dataset"
    assert source["landing_page"].startswith("https://")
    assert source["custodian_catalogue"].startswith("https://")
    assert access["metadata_found"] is True
    assert access["raw_files_obtained"] is False
    assert access["machine_readable_schema_obtained"] is False
    assert access["license_terms_obtained"] is False
    assert eligibility["full_loop_external_holdout_eligible"] is False
    assert record["gate_impact"] == "full_loop_external_validation_remains_open"
    assert "raw-data access" in record["claim_boundary"]


def test_request_draft_contains_prospective_freeze_and_rights_requirements():
    draft = (
        ROOT / "research/NBSDC_HRS_OPERATIONAL_DATASET_DATA_REQUEST_DRAFT_2026_10_06.md"
    ).read_text(encoding="utf-8")
    for required in (
        "공통 타임베이스",
        "차량 또는 리셉터클",
        "서면 사용 조건",
        "결과를\n열기 전에 고정",
        "보정·시간 왜곡·사후",
    ):
        assert required in draft
