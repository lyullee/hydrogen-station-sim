"""Build a privacy-bounded, reproducible data-coverage summary.

The project has several independently audited public and owner-controlled
artifacts.  This report joins only their aggregate fields so a reviewer can
see what the current evidence supports without exposing private paths, tags,
raw rows, or site identity.  It is deliberately a reporting tool: it does not
change runtime parameters or promote a component diagnostic to full-loop
validation.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _read(root: Path, relative: str) -> dict[str, Any]:
    path = root / relative
    return json.loads(path.read_text(encoding="utf-8"))


def build_summary(root: Path) -> dict[str, Any]:
    readiness = _read(root, "research/ijhe_readiness_audit.json")
    local = _read(
        root,
        "research/local_confidential_station_data_utilization_2026_10_08.json",
    )
    replay = _read(root, "research/local_station_runtime_profile_integration_2026_10_09.json")
    tank = _read(root, "research/public_type_iv_tank_runtime_calibration_2026_10_07.json")
    accidents = _read(root, "research/runtime_public_accident_precedent_routing_2026_10_07.json")
    methytrucks = _read(root, "research/methytrucks_2026_public_measurement_intake.json")
    benchmarks = _read(
        root,
        "research/public_experimental_benchmarks_2026_10_06.json",
    )
    hytf = _read(root, "research/hytf_open_tank_trace_boundary_2026_10_05.json")
    h2safe = _read(root, "research/h2safe_public_dataset_intake_2026_10_08.json")
    nrel_boundary = _read(root, "research/nrel_hdvs_raw_trace_boundary_2026_10_05.json")
    nrel_result = _read(
        root,
        "research/nrel_hdvs_boundary_screen_2026_10_10.json",
    )
    type_i_filling = _read(
        root,
        "research/striednig_hyddown_diagnostic_result_2026_10_10.json",
    )
    station_side_integrated = _read(
        root,
        "research/confidential_station_side_integrated_validation_2026_10_09.json",
    )
    nbsdc_liquid = _read(
        root,
        "research/nbsdc_liquid_hrs_public_access_recheck_2026_10_10.json",
    )

    inventory = local["inventory"]
    utilization = local["utilization"]
    gate_counts = readiness["gate_counts"]
    component_aggregate = methytrucks.get("aggregate", {})
    nist = next(
        (
            item
            for item in benchmarks.get("sources") or []
            if isinstance(item, dict)
            and item.get("id") == "NIST_FTS_2015_FIELD_METROLOGY"
        ),
        {},
    )
    nist_aggregate = nist.get("aggregate") if isinstance(nist, dict) else {}
    if not isinstance(nist_aggregate, dict):
        nist_aggregate = {}
    usn = next(
        (
            item
            for item in benchmarks.get("sources") or []
            if isinstance(item, dict)
            and item.get("id") == "USN_OPEN_CHANNEL_ACTUAL_H2_2025"
        ),
        {},
    )
    usn_aggregate = usn.get("aggregate") if isinstance(usn, dict) else {}
    if not isinstance(usn_aggregate, dict):
        usn_aggregate = {}
    usn_coordinates = usn.get("coordinate_metadata") if isinstance(usn, dict) else {}
    if not isinstance(usn_coordinates, dict):
        usn_coordinates = {}
    hytf_experiment = hytf.get("experiment") if isinstance(hytf, dict) else {}
    if not isinstance(hytf_experiment, dict):
        hytf_experiment = {}
    hytf_channels = hytf_experiment.get("channels") or {}
    hytf_ranges = hytf_experiment.get("observed_ranges") or {}
    h2safe_intake = h2safe.get("intake") if isinstance(h2safe, dict) else {}
    if not isinstance(h2safe_intake, dict):
        h2safe_intake = {}
    nrel_experiment = nrel_boundary.get("experiment") if isinstance(nrel_boundary, dict) else {}
    if not isinstance(nrel_experiment, dict):
        nrel_experiment = {}
    nrel_boundary_check = nrel_boundary.get("boundary_check") if isinstance(nrel_boundary, dict) else {}
    if not isinstance(nrel_boundary_check, dict):
        nrel_boundary_check = {}
    nrel_eligibility = nrel_boundary.get("eligibility") if isinstance(nrel_boundary, dict) else {}
    if not isinstance(nrel_eligibility, dict):
        nrel_eligibility = {}
    nrel_aggregate = nrel_result.get("aggregate") if isinstance(nrel_result, dict) else {}
    if not isinstance(nrel_aggregate, dict):
        nrel_aggregate = {}
    nrel_screen_limits = nrel_result.get("screening_limits") if isinstance(nrel_result, dict) else {}
    if not isinstance(nrel_screen_limits, dict):
        nrel_screen_limits = {}
    nrel_frozen_model = nrel_result.get("frozen_model") if isinstance(nrel_result, dict) else {}
    if not isinstance(nrel_frozen_model, dict):
        nrel_frozen_model = {}
    type_i_eligibility = type_i_filling.get("eligibility") if isinstance(type_i_filling, dict) else {}
    if not isinstance(type_i_eligibility, dict):
        type_i_eligibility = {}
    station_side_checks = station_side_integrated.get("checks") if isinstance(station_side_integrated, dict) else {}
    if not isinstance(station_side_checks, dict):
        station_side_checks = {}
    station_side_decision = station_side_integrated.get("decision") if isinstance(station_side_integrated, dict) else {}
    if not isinstance(station_side_decision, dict):
        station_side_decision = {}
    nbsdc_metadata = nbsdc_liquid.get("metadata_observation") if isinstance(nbsdc_liquid, dict) else {}
    if not isinstance(nbsdc_metadata, dict):
        nbsdc_metadata = {}
    nbsdc_access = nbsdc_liquid.get("access_probe") if isinstance(nbsdc_liquid, dict) else {}
    if not isinstance(nbsdc_access, dict):
        nbsdc_access = {}
    return {
        "schema_version": 1,
        "artifact_type": "privacy_bounded_data_coverage_summary",
        "generated_at": "2026-10-10",
        "privacy": {
            "source_paths_published": False,
            "source_filenames_published": False,
            "source_headers_published": False,
            "raw_rows_persisted": False,
            "site_company_manufacturer_published": False,
            "absolute_timestamps_published": False,
        },
        "readiness": {
            "ijhe_gate_counts": gate_counts,
            "bounded_submission_ready": bool(readiness["bounded_ijhe_submission_ready"]),
            "full_user_objective_ready": bool(readiness["full_user_objective_ready"]),
        },
        "validated_or_actionable_now": [
            {
                "id": "owner_station_side_dynamics",
                "status": "ACTIONABLE",
                "evidence": "research/local_confidential_station_data_utilization_2026_10_08.json",
                "coverage": {
                    "deduplicated_rows": inventory["deduplicated_data_rows"],
                    "ordered_high_bank_pressure_cycles": utilization["ordered_high_bank_pressure_cycles"],
                    "paired_medium_high_pressure_episodes": utilization["paired_medium_high_pressure_episodes"],
                    "short_horizon_pressure_forecast_cases": utilization["short_horizon_pressure_forecast_cases"],
                    "conditional_recharge_flow_episodes": utilization["conditional_recharge_flow_episodes"],
                },
                "allowed_claim": "station-side pressure, cascade and recharge dynamics diagnostics",
                "not_allowed": "vehicle-side full-loop accuracy or field safety limits",
            },
            {
                "id": "owner_station_runtime_replay",
                "status": "ACTIONABLE",
                "evidence": "research/local_station_runtime_profile_integration_2026_10_09.json",
                "coverage": {
                    "reference_defaults_completed": replay["checks"]["reference_defaults_preserved"],
                    "opt_in_profile_completed": replay["checks"]["opt_in_profile_applied"],
                    "failed_dynamics_profile_detached": replay["checks"]["failed_dynamics_profile_not_attached"],
                    "simulations_completed": replay["checks"]["simulations_completed"],
                },
                "allowed_claim": "sanitized station pressure-boundary profile is wired and replayable",
                "not_allowed": "automatic runtime parameter replacement or full-loop validation",
            },
            {
                "id": "public_type_iv_tank",
                "status": "VALIDATED_COMPONENT",
                "evidence": "research/public_type_iv_tank_runtime_calibration_2026_10_07.json",
                "coverage": {
                    "validation_case_count": tank["runtime"]["validation_case_count"],
                    "runtime_match": tank["runtime_match"],
                    "evidence_status": tank["runtime"]["llm_evidence_status"],
                },
                "allowed_claim": "measured-boundary Type-IV tank component validation",
                "not_allowed": "station controller, compressor, cascade, dispenser or field safety certification",
            },
            {
                "id": "public_station_tank_boundary",
                "status": "DIAGNOSTIC_ONLY",
                "evidence": "research/nrel_hdvs_raw_trace_boundary_2026_10_05.json",
                "coverage": {
                    "sample_count": nrel_experiment.get("nonempty_timed_row_count"),
                    "duration_s": (nrel_experiment.get("time_range_s") or [None, None])[-1],
                    "tank_count": len(nrel_experiment.get("tank_ids") or []),
                    "hose_pressure_temperature_present": nrel_boundary_check.get(
                        "hose_pressure_and_temperature_present", False
                    ),
                    "tank_pressure_temperature_mass_present": nrel_boundary_check.get(
                        "tank_pressure_temperature_mass_present", False
                    ),
                    "partial_station_to_tank_boundary_eligible": nrel_eligibility.get(
                        "partial_station_to_tank_boundary_eligible", False
                    ),
                    "full_loop_holdout_eligible": nrel_boundary_check.get(
                        "full_loop_external_holdout_eligible", False
                    ),
                    "screening_status": (
                        "diagnostic_only_failed_screen"
                        if nrel_aggregate.get("screening_pass_count") == 0
                        else "diagnostic_only_partial_screen"
                    ),
                    "screening_pass_count": nrel_aggregate.get("screening_pass_count"),
                    "screening_pass_fraction": nrel_aggregate.get("screening_pass_fraction"),
                    "pressure_rmse_mpa": nrel_aggregate.get("pressure_rmse_mpa"),
                    "temperature_rmse_c": nrel_aggregate.get("temperature_rmse_c"),
                    "mass_rmse_kg": nrel_aggregate.get("mass_rmse_kg"),
                    "pressure_final_error_mpa": nrel_aggregate.get("pressure_final_error_mpa"),
                    "screening_limits": {
                        "pressure_rmse_mpa_max": nrel_screen_limits.get("pressure_rmse_mpa_max"),
                        "temperature_rmse_c_max": nrel_screen_limits.get("temperature_rmse_c_max"),
                        "mass_final_abs_error_kg_max": nrel_screen_limits.get("mass_final_abs_error_kg_max"),
                    },
                    "parameter_tuning": nrel_frozen_model.get("post_access_parameter_tuning") is True,
                },
                "allowed_claim": "공통시계 호스·수용탱크 압력·온도·질량의 부분 station-to-tank 경계 진단",
                "not_allowed": "충전소 제어기·캐스케이드·ESD·노즐/리셉터클을 포함한 full-loop 검증",
            },
            {
                "id": "owner_station_side_integrated_validation",
                "status": "VALIDATED_STATION_SIDE",
                "evidence": "research/confidential_station_side_integrated_validation_2026_10_09.json",
                "coverage": {
                    "pressure_boundary_holdout_supported": bool(
                        (station_side_checks.get("pressure_boundary") or {}).get("supported")
                    ),
                    "pressure_boundary_holdout_points": (
                        station_side_checks.get("pressure_boundary") or {}
                    ).get("holdout_points"),
                    "cascade_sequence_holdout_supported": bool(
                        (station_side_checks.get("cascade_sequence") or {}).get("supported")
                    ),
                    "cascade_sequence_holdout_pairs": (
                        station_side_checks.get("cascade_sequence") or {}
                    ).get("holdout_pairs"),
                    "recharge_pressure_forecast_supported": bool(
                        (station_side_checks.get("recharge_pressure_forecast") or {}).get("supported")
                    ),
                    "recharge_pressure_forecast_holdout_cases": (
                        station_side_checks.get("recharge_pressure_forecast") or {}
                    ).get("holdout_cases"),
                    "lifecycle_counter_alignment_supported": bool(
                        (station_side_checks.get("lifecycle_alignment") or {}).get(
                            "counter_monotonicity_met"
                        )
                    ),
                    "runtime_parameter_application": bool(
                        station_side_decision.get("runtime_parameter_application")
                    ),
                    "vehicle_fill_validation": bool(
                        station_side_decision.get("vehicle_fill_validation")
                    ),
                    "full_loop_external_validation_supported": bool(
                        station_side_decision.get("full_loop_external_validation_supported")
                    ),
                },
                "allowed_claim": "hash-linked same-site station-side pressure-boundary, cascade-sequence and recharge-pressure holdout integration",
                "not_allowed": "vehicle-side accuracy, full station-to-vehicle validation, safety-distance or field certification; the retained lifecycle-counter result is negative",
            },
            {
                "id": "nbsdc_liquid_hrs_catalogue",
                "status": "REQUEST_CANDIDATE",
                "evidence": "research/nbsdc_liquid_hrs_public_access_recheck_2026_10_10.json",
                "coverage": {
                    "catalogue_record_verified": nbsdc_liquid.get("status")
                    == "REAL_LHRS_METADATA_CONFIRMED_NUMERICAL_FILES_APPLICATION_CONTROLLED",
                    "monitoring_window_hours": 16,
                    "sample_interval_s": 1,
                    "file_count": nbsdc_metadata.get("file_count"),
                    "raw_synchronized_archive_located": bool(
                        nbsdc_access.get("raw_numerical_files_obtained")
                    ),
                    "numerical_file_access": "application_required",
                },
                "allowed_claim": "real liquid-hydrogen refueling-station operating-range and data-access lead for station-side schema/context and LLM claim-boundary grounding",
                "not_allowed": "numerical model calibration, independent holdout scoring, full station-to-vehicle validation, safety-distance calculation, or response-effectiveness claim before custodian approval and channel attestation",
            },
            {
                "id": "public_component_measurements",
                "status": "DIAGNOSTIC_ONLY",
                "evidence": "research/methytrucks_2026_public_measurement_intake.json",
                "coverage": {
                    "workbook_count": component_aggregate.get("workbook_count"),
                    "sample_count": component_aggregate.get("sample_count"),
                    "mass_closure_comparable_pass_fraction": component_aggregate.get(
                        "mass_closure_comparable_pass_fraction"
                    ),
                },
                "allowed_claim": "public synchronized component pressure/temperature/flow diagnostics",
                "not_allowed": "prospective station-to-vehicle holdout",
            },
            {
                "id": "public_type_i_filling_thermal",
                "status": "DIAGNOSTIC_ONLY",
                "evidence": "research/striednig_hyddown_diagnostic_result_2026_10_10.json",
                "coverage": {
                    "case_count": len(type_i_filling.get("cases") or []),
                    "gas_temperature_rmse_k": [
                        (case.get("metrics") or {}).get("gas_temperature_rmse_k")
                        for case in type_i_filling.get("cases") or []
                    ],
                    "gas_temperature_peak_absolute_error_k": [
                        (case.get("metrics") or {}).get(
                            "gas_temperature_peak_absolute_error_k"
                        )
                        for case in type_i_filling.get("cases") or []
                    ],
                    "runtime_parameter_application": type_i_eligibility.get(
                        "runtime_parameter_application", False
                    ),
                    "full_loop_holdout_eligible": type_i_eligibility.get(
                        "full_loop_station_vehicle_validation_eligible", False
                    ),
                },
                "allowed_claim": "공개 Type-I 탱크 충전 열거동의 구성품 진단 및 열 모델 비교",
                "not_allowed": "충전소 제어기·캐스케이드·디스펜서·차량을 포함한 full-loop 검증 또는 런타임 파라미터 승격",
            },
            {
                "id": "public_field_metrology",
                "status": "DIAGNOSTIC_ONLY",
                "evidence": "research/public_experimental_benchmarks_2026_10_06.json",
                "coverage": {
                    "field_draft_count": nist_aggregate.get("field_draft_count"),
                    "pressure_mpa_range": [
                        nist_aggregate.get("field_pressure_mpa_min"),
                        nist_aggregate.get("field_pressure_mpa_max"),
                    ],
                    "mass_groups_kg": nist_aggregate.get("field_draft_mass_groups_kg"),
                    "maximum_method_agreement_percent": nist_aggregate.get(
                        "field_method_agreement_max_percent"
                    ),
                },
                "allowed_claim": "35 MPa 현장 계측의 압력·온도·질량 경계 및 반복성 맥락",
                "not_allowed": "원시 station-to-vehicle holdout, 제어기·ESD·사고영향 검증",
            },
            {
                "id": "public_actual_h2_spatial_dispersion",
                "status": "DIAGNOSTIC_ONLY",
                "evidence": "research/public_experimental_benchmarks_2026_10_06.json",
                "coverage": {
                    "archive_count": usn_aggregate.get("archive_count"),
                    "total_rows_screened": usn_aggregate.get("total_rows_screened"),
                    "sensor_count_per_archive": usn_aggregate.get("sensor_count_per_archive"),
                    "median_sample_interval_s": usn_aggregate.get("median_sample_interval_s"),
                    "sensor_coordinate_count": usn_coordinates.get("sensor_coordinate_count"),
                    "machine_readable_sensor_coordinates_public": usn_coordinates.get(
                        "machine_readable_sensor_coordinates_public", False
                    ),
                    "spatial_holdout_ready": usn_coordinates.get("spatial_holdout_ready", False),
                },
                "allowed_claim": "실제 수소 저압 누출·다중 검지기 응답 범위와 사고 모델 진단",
                "not_allowed": "충전소 full-loop, 좌표기반 검지기 holdout, site-specific safety distance",
            },
            {
                "id": "public_hytf_tank_boundary",
                "status": "DIAGNOSTIC_ONLY",
                "evidence": "research/hytf_open_tank_trace_boundary_2026_10_05.json",
                "coverage": {
                    "sample_count": hytf_experiment.get("sample_count"),
                    "duration_s": hytf_experiment.get("duration_s"),
                    "pressure_channel_count": len(hytf_channels.get("pressure_channels") or []),
                    "tank_thermocouple_count": len(hytf_channels.get("tank_thermocouples") or []),
                    "pressure_bar_range": [
                        min(hytf_ranges.get("p_1_bar") or [None]),
                        max(hytf_ranges.get("p_1_bar") or [None]),
                    ],
                },
                "allowed_claim": "공개 70 MPa 탱크 압력·열 응답의 구성품 경계 진단",
                "not_allowed": "질량유량, 차량 수용부, 충전소 제어기·ESD를 포함한 full-loop 검증",
            },
            {
                "id": "public_h2safe_indoor_surrogate",
                "status": "DIAGNOSTIC_ONLY",
                "evidence": "research/h2safe_public_dataset_intake_2026_10_08.json",
                "coverage": {
                    "laboratory_count": h2safe_intake.get("laboratory_count"),
                    "test_count": h2safe_intake.get("test_count"),
                    "total_time_series_rows": h2safe_intake.get("total_time_series_rows"),
                    "lab_declared_channel_counts": h2safe_intake.get("labs") and {
                        str(lab.get("lab_id")): next(
                            (
                                test.get("declared_channel_count")
                                for test in (lab.get("tests") or [])
                                if test.get("declared_channel_count") is not None
                            ),
                            None,
                        )
                        for lab in (h2safe_intake.get("labs") or [])
                    },
                },
                "allowed_claim": "헬륨 대체가스의 실내 센서 응답·좌표 진단",
                "not_allowed": "수소 농도 환산, 충전소 외부 확산, ESD 효과 또는 안전거리 검증",
            },
            {
                "id": "public_accident_precedents",
                "status": "ROUTED_FOR_GROUNDING",
                "evidence": "research/runtime_public_accident_precedent_routing_2026_10_07.json",
                "coverage": {
                    "public_report_count": accidents["aggregate"]["public_report_count"],
                    "mapped_response_family_count": accidents["aggregate"]["mapped_response_family_count"],
                    "runtime_routed_case_references": accidents["aggregate"]["runtime_routed_case_references"],
                    "unmatched_response_family_count": accidents["aggregate"]["unmatched_response_family_count"],
                },
                "allowed_claim": "traceable scenario and response-plan grounding",
                "not_allowed": "historical frequency or response-effectiveness estimation",
            },
        ],
        "minimum_next_input": {
            "purpose": "close the independent station-to-vehicle validation gate",
            "event_count": 3,
            "required_channels": [
                "common elapsed time",
                "station or dispenser pressure",
                "delivered-gas or boundary temperature",
                "mass flow or transferred mass",
                "protocol start/stop phase",
            ],
            "preferred_channels": [
                "vehicle/receptacle pressure and temperature",
                "selected cascade-bank state",
                "precooler outlet temperature",
                "ESD and fault transitions",
            ],
            "privacy_route": "custodian-run export or de-identified component bundle outside the repository",
            "evaluation_rule": "freeze protocol and model before scoring; never fit on the holdout",
        },
        "privacy_safe_export_contract": {
            "purpose": "작은 비식별 이벤트 묶음으로 full-loop 외부 검증을 닫기 위한 최소 계약",
            "validator": "src/h2station/privacy_safe_full_loop_intake.py",
            "validator_status": "implemented_and_tested",
            "guide": "research/PRIVACY_SAFE_FULL_LOOP_INTAKE_2026_10_10.md",
            "custodian_keeps_raw_data": True,
            "repository_receives_only": [
                "pseudonymous event id",
                "elapsed time from event start",
                "unit-normalized channel names",
                "channel-role attestation",
                "file hash and row count",
                "aggregate validation metrics",
            ],
            "must_not_include": [
                "site or company identity",
                "manufacturer or equipment serial",
                "calendar timestamps",
                "raw rows unless separately approved",
            ],
            "minimum_event_bundle": 3,
            "why_this_is_enough": "세 이벤트를 동일한 사전 동결 프로토콜로 평가하면 차량 경계 유무와 generalization을 확인할 수 있으며, 전체 원시 히스토리 공개가 필요하지 않다.",
        },
        "decision": {
            "data_volume_is_primary_blocker": False,
            "current_primary_gap": "synchronized and attested receiving-vessel/vehicle channels",
            "continue_component_validation": True,
            "full_loop_gate_remains_open": True,
            "goal_completion_permitted": False,
            "data_acquisition_message": "추가 데이터의 우선순위는 양이 아니라 동기화된 수용부 채널과 역할 증명이다.",
        },
        "claim_boundary": (
            "This summary joins audited aggregate evidence only. It does not expose raw data, "
            "identify a site or company, establish safety distances, or convert component and "
            "station-side evidence into a full station-to-vehicle validation claim."
        ),
    }


def _markdown(summary: dict[str, Any]) -> str:
    counts = summary["readiness"]["ijhe_gate_counts"]
    lines = [
        "# Privacy-bounded data coverage summary (2026-10-10)",
        "",
        "이 문서는 확보된 공개·비식별 자료로 지금 검증할 수 있는 범위와, 완전한 충전소-차량 검증에 필요한 최소 입력을 자동으로 정리한 산출물이다.",
        "",
        f"- IJHE 게이트: PASS {counts['PASS']} / FAIL {counts['FAIL']} / PENDING {counts['PENDING']}",
        f"- 데이터 양이 주된 병목인가: {'아니오' if not summary['decision']['data_volume_is_primary_blocker'] else '예'}",
        f"- 현재 주된 공백: {summary['decision']['current_primary_gap']}",
        "- 현실적인 최소 데이터 요청: [DATA_ACQUISITION_MINIMUM_2026_10_10.md](DATA_ACQUISITION_MINIMUM_2026_10_10.md)",
        "",
        "## 현재 사용 가능한 검증 범위",
        "",
        "| 영역 | 상태 | 현재 가능한 주장 | 금지된 주장 |",
        "| --- | --- | --- | --- |",
    ]
    for item in summary["validated_or_actionable_now"]:
        lines.append(
            f"| `{item['id']}` | {item['status']} | {item['allowed_claim']} | {item['not_allowed']} |"
        )
    minimum = summary["minimum_next_input"]
    lines.extend(
        [
            "",
            "## 다음 최소 입력",
            "",
            f"전체 히스토리언 대신, 공통 시간축을 가진 충전 이벤트 {minimum['event_count']}건부터 요청한다.",
            "",
            "필수 채널: " + ", ".join(minimum["required_channels"]) + ".",
            "",
            "선택 채널: " + ", ".join(minimum["preferred_channels"]) + ".",
            "",
            f"평가 원칙: {minimum['evaluation_rule']}",
            "",
            "## 판정",
            "",
            "현재 자료로 설비·저장뱅크·탱크·검지기·사고 대응 근거는 계속 보강할 수 있다. 데이터 양이 주된 병목은 아니며, 완전한 IJHE 수준의 충전소-차량 외부 검증에 필요한 것은 차량 측 채널의 동기화·의미·재사용 권한이다.",
            "",
            "공개 카탈로그에서 실제 액체수소 충전소 운전 데이터 후보를 확인했지만, 수치 파일은 데이터 신청 승인 전까지 잠겨 있다. 따라서 현재는 운전범위·파일 역할·접근 경계만 LLM 근거로 사용하고, 원자료를 받기 전에는 수치 보정이나 성능 주장을 하지 않는다.",
            "",
            "원시 데이터를 공개하기 어렵다면 custodian이 원시 파일을 보관한 채, 비식별 이벤트 3건의 해시·역할 증명·집계 지표만 전달하는 방식으로 검증을 진행한다.",
            "",
            "원시 행, 경로, 회사·사이트·제조사 식별자는 이 요약에 포함하지 않는다.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--json-output", type=Path, required=True)
    parser.add_argument("--markdown-output", type=Path, required=True)
    args = parser.parse_args()
    summary = build_summary(args.root.resolve())
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_output.write_text(_markdown(summary), encoding="utf-8")
    print(args.json_output)
    print(args.markdown_output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
