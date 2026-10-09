from __future__ import annotations

import json
from pathlib import Path

from h2station.llm_grounding import build_evidence_manifest, prompt_evidence_summary


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


def test_public_operational_leads_are_routed_to_llm_without_full_loop_upgrade() -> None:
    manifest = build_evidence_manifest(
        {
            "time_s": 1.0,
            "header_pressure_mpa": 45.0,
            "header_temperature_c": 25.0,
            "header_mass_kg": 10.0,
            "header_inflow_g_s": 0.0,
        },
        {},
        [],
        False,
        question="공개 운전 근거를 사용해 현재 상태를 설명해줘",
    )
    evidence = manifest["response_evidence"]["public_operational_evidence_leads"]
    assert evidence["decision"] == "NO_NEW_ELIGIBLE_PUBLIC_RAW_FULL_LOOP_SET_IDENTIFIED"
    assert evidence["full_loop_external_validation_supported"] is False
    assert evidence["dynamic_model_parameter_calibration_eligible"] is False
    assert {item["id"] for item in evidence["sources"]} == {
        "carb_2024_hrs_inuse_report",
        "nist_transient_flow_facility",
    }
    summary = prompt_evidence_summary(manifest)
    assert "public_operational_evidence_leads" in summary
    rendered = json.dumps(summary, ensure_ascii=False)
    assert "raw_synchronized_archive_located" in rendered
    assert "C:\\" not in rendered
