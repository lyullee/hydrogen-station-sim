from __future__ import annotations

import json
from pathlib import Path

from h2station.llm_grounding import (
    build_evidence_manifest,
    prompt_decision_evidence,
    prompt_evidence_header,
    prompt_evidence_summary,
)
from h2station.local_evidence import public_evidence_inventory_summary


ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT / "research/striednig_hyddown_diagnostic_result_2026_10_10.json"


def test_striednig_diagnostic_is_aggregate_only_and_keeps_claim_boundary() -> None:
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    assert result["artifact_type"] == "public_type_i_filling_thermal_diagnostic"
    assert result["evidence_role"] == "post_access_public_component_diagnostic"
    assert len(result["cases"]) == 3
    assert all(case["measurement_count"] > 0 for case in result["cases"])
    assert all("source_sha256" in case for case in result["cases"])
    assert result["eligibility"]["raw_measurement_arrays_persisted"] is False
    assert result["eligibility"]["runtime_parameter_application"] is False
    assert result["eligibility"]["validation_gate_changed"] is False
    assert result["eligibility"]["full_loop_station_vehicle_validation_eligible"] is False
    assert "does not validate station control" in result["claim_boundary"]


def test_striednig_diagnostic_is_available_to_llm_with_explicit_scope() -> None:
    manifest = build_evidence_manifest(
        {
            "time_s": 10.0,
            "header_pressure_mpa": 70.0,
            "header_temperature_c": 25.0,
            "header_mass_kg": 1.0,
            "nozzle_flow_g_s": 0.0,
        },
        {},
        [],
        False,
        question="공개 수소 충전 실험 데이터로 온도 거동을 비교해줘",
    )

    evidence = manifest["response_evidence"]["public_type_i_filling_diagnostic"]
    assert evidence["evidence_role"] == "public Type-I filling thermal component diagnostic"
    assert len(evidence["cases"]) == 3
    assert evidence["runtime_parameter_application"] is False
    assert evidence["full_loop_external_holdout_eligible"] is False

    summary = prompt_evidence_summary(manifest)["public_type_i_filling_diagnostic"]
    assert len(summary["cases"]) == 3
    assert summary["full_loop_external_holdout_eligible"] is False

    header = prompt_evidence_header(manifest)
    assert any(
        link["id"] == "PUBLIC_STRIEDNIG_TYPE_I_FILLING"
        for link in header["public_source_links"]
    )

    decision = prompt_decision_evidence(manifest)
    compact = decision["decision_support_evidence"]["public_type_i_filling_diagnostic"]
    assert compact["runtime_parameter_application"] is False
    assert compact["full_loop_external_holdout_eligible"] is False


def test_public_inventory_reports_type_i_diagnostic_without_promoting_full_loop_gate() -> None:
    inventory = public_evidence_inventory_summary()
    diagnostic = inventory["public_type_i_filling_diagnostic"]
    assert diagnostic["status"] == "available"
    assert diagnostic["case_count"] == 3
    assert diagnostic["runtime_parameter_application"] is False
    assert diagnostic["full_loop_holdout_eligible"] is False
