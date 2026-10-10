from __future__ import annotations

import json

from h2station.full_loop_bundle_evidence import full_loop_bundle_evidence
from h2station.llm_grounding import (
    build_evidence_manifest,
    prompt_decision_evidence,
    prompt_evidence_header,
    prompt_evidence_summary,
)


def _receipt() -> dict:
    return {
        "schema_version": 1,
        "artifact_type": "controlled_deidentified_hrs_full_loop_export_receipt",
        "controlled_access_only": True,
        "source_identifiers_published": False,
        "absolute_timestamps_published": False,
        "original_column_names_published": False,
        "raw_rows_persisted_in_repository": False,
        "temperature_observation_semantics_attested": True,
        "rows": 120,
        "time_duration_s": 60.0,
        "station_to_vehicle_trace_ready": True,
        "cascade_dispatch_evaluable": True,
        "full_loop_trace_ready": True,
        "evaluation_scope": "cascade_resolved_station_to_vehicle",
        "intake_decision": "QUALITY_SCREEN_PASS",
        "quality_decision": "FULL_LOOP_TRACE_READY_FOR_EVALUATION",
        "trace_sha256": "private-trace-hash",
        "claim_boundary": "private source path and site name",
    }


def _result() -> dict:
    return {
        "schema_version": 1,
        "artifact_type": "controlled_hrs_frozen_evaluation_result",
        "raw_rows_persisted": False,
        "source_identifiers_published": False,
        "absolute_timestamps_published": False,
        "evaluation_scope": "cascade_resolved_station_to_vehicle",
        "decision": "FROZEN_EVALUATION_PASS",
        "model_sample_count": 120,
        "observed_sample_count": 120,
        "trace_sha256": "private-trace-hash",
        "metrics": {
            "vehicle_pressure_mpa": {
                "sample_count": 120,
                "rmse": 0.2,
                "mae": 0.1,
                "final_error": 0.0,
            }
        },
        "acceptance_by_metric": {"vehicle_pressure_mpa": True},
        "claim_boundary": "private claim boundary",
    }


def test_full_loop_receipt_and_result_are_sanitized_and_grounded() -> None:
    receipt = _receipt()
    result = _result()
    sanitized = full_loop_bundle_evidence({
        "full_loop_receipt": receipt,
        "full_loop_result": result,
    })
    assert sanitized is not None
    rendered = json.dumps(sanitized, ensure_ascii=False)
    assert "private-trace-hash" not in rendered
    assert "private source path" not in rendered
    assert sanitized["full_loop_external_validation_supported"] is False
    assert sanitized["frozen_evaluation_result"]["decision"] == "FROZEN_EVALUATION_PASS"

    manifest = build_evidence_manifest(
        {"time_s": 1.0, "full_loop_receipt": receipt, "full_loop_result": result},
        {}, [], False, question="차량 충전 실측 데이터 검증",
    )
    response = manifest["response_evidence"]["confidential_full_loop_bundle"]
    assert response["full_loop_trace_ready"] is True
    assert response["full_loop_external_validation_supported"] is False
    assert prompt_evidence_summary(manifest)["confidential_full_loop_bundle"]["rows"] == 120
    assert prompt_decision_evidence(manifest)["decision_support_evidence"][
        "confidential_full_loop_bundle"
    ]["frozen_evaluation_required"] is True
    assert prompt_evidence_header(manifest)["confidential_full_loop_bundle"][
        "evaluation_scope"
    ] == "cascade_resolved_station_to_vehicle"


def test_full_loop_receipt_fails_closed_without_privacy_attestation() -> None:
    receipt = _receipt()
    receipt["raw_rows_persisted_in_repository"] = True
    assert full_loop_bundle_evidence({"full_loop_receipt": receipt}) is None


def test_missing_receipt_is_explicitly_bounded_for_llm() -> None:
    evidence = full_loop_bundle_evidence({})
    assert evidence is not None
    assert evidence["status"] == "unavailable"
    assert evidence["availability_reason"] == "NO_AUTHORIZED_EXTERNAL_RECEIPT"
    assert evidence["full_loop_holdout_eligible"] is False
    assert evidence["full_loop_external_validation_supported"] is False
    assert len(evidence["required_input_groups"]) >= 4

    manifest = build_evidence_manifest({"time_s": 1.0}, {}, [], False)
    bounded = prompt_evidence_summary(manifest)["confidential_full_loop_bundle"]
    assert bounded["status"] == "unavailable"
    assert bounded["full_loop_holdout_eligible"] is False
    assert bounded["required_input_groups"]
