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
