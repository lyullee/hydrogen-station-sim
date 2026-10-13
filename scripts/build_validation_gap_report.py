"""Build a privacy-bounded triage of the current validation gates.

This is a decision-support report, not a new validation run.  It reads the
authoritative readiness audit and emits only gate-level status, aggregate
metrics and the next minimum action.  Evidence paths, raw rows and identity
fields are intentionally excluded from the generated report.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


_FULL_LOOP = {
    "full_loop_external_validation",
}

_MODEL = {
    "dickens_typeiii_prospective_validation",
    "h2safe_spatial_detector_transfer_validation",
    "hytunnel_carpark_dispersion_validation",
    "hytunnel_carpark_mass_flow_validation",
    "preslhy_blowdown_external_validation",
    "preslhy_partb_ambient_external_validation",
    "preslhy_revised_holdout_validation",
    "proust_independent_release_validation",
    "schefer_transient_release_validation",
    "schefer_2007_pressure_decay_validation",
    "grune_2014_pressure_decay_validation",
}

_GOVERNANCE = {
    "institutional_ethics_determination",
    "hiad_casebook_frozen",
    "hiad_holdout_collection",
    "independent_expert_review_complete",
    "saga_effectiveness_and_safety_supported",
    "submission_metadata_and_declarations",
}

_OPTIONAL_HUMAN_EVALUATION = {
    "institutional_ethics_determination",
    "hiad_casebook_frozen",
    "hiad_holdout_collection",
    "independent_expert_review_complete",
    "saga_effectiveness_and_safety_supported",
}

_GRUNE_SECONDARY_RESULT = "research/grune_2014_secondary_public_figure_result_2026_10_12.json"

# Keep the status report usable as an execution queue.  The synchronized
# station-to-vehicle lane was explicitly removed from the primary objective
# after the public-data search; retain its legacy FAIL only in a separate
# scope-exclusion list.  The active queue therefore starts with component
# physics and then governance work instead of repeatedly asking for data that
# the current paper does not require.
_TRACKS = {
    "component_model": {
        "priority": "P0",
        "parallel_track": "component_model_repairs",
        "why_now": "현재 주 목표에 포함된 실패 물리량별 독립 holdout을 병행하고, 통과 전 런타임 승격을 막음",
    },
    "governance_review": {
        "priority": "P1",
        "parallel_track": "review_and_publication",
        "why_now": "수치 계산과 독립적으로 진행 가능한 검토·기록 작업",
    },
}


def _read(root: Path, relative: str) -> dict[str, Any]:
    return json.loads((root / relative).read_text(encoding="utf-8"))


def _secondary_diagnostics(root: Path) -> list[dict[str, Any]]:
    """Expose transparent secondary diagnostics without changing gate status.

    These are post-outcome figure-derived checks, not primary validation
    evidence.  Keeping them beside the triage prevents the queue from
    becoming stale while preserving the frozen primary claim boundary.
    """

    path = root / _GRUNE_SECONDARY_RESULT
    if not path.exists():
        return []
    result = _read(root, _GRUNE_SECONDARY_RESULT)
    metrics = result.get("result") or {}
    return [
        {
            "id": "grune_2014_secondary_public_figure_diagnostic",
            "source_gate": "grune_2014_pressure_decay_validation",
            "status": "DIAGNOSTIC_ONLY",
            "points": metrics.get("points"),
            "pressure_nrmse_percent_initial_measured": metrics.get(
                "pressure_nrmse_percent_initial_measured"
            ),
            "median_absolute_percentage_error_percent": metrics.get(
                "median_absolute_percentage_error_percent"
            ),
            "half_pressure_time_relative_error_percent": metrics.get(
                "half_pressure_time_relative_error_percent"
            ),
            "joint_primary_screen_pass": bool(metrics.get("joint_primary_screen_pass")),
            "primary_gate_unchanged": True,
            "claim_boundary": str(result.get("claim_boundary", "")),
        }
    ]


def _bucket(gate_id: str) -> str:
    if gate_id in _FULL_LOOP:
        return "full_loop_data"
    if gate_id in _MODEL:
        return "component_model"
    if gate_id in _GOVERNANCE:
        return "governance_review"
    return "other"


def _next_action(gate_id: str, status: str) -> str:
    if gate_id == "full_loop_external_validation":
        return (
            "동기화된 충전 이벤트 최소 3건부터 비식별 intake로 접수한다. "
            "수용부 압력·온도와 protocol_phase가 없으면 full-loop 주장을 열지 않는다."
        )
    if gate_id in {"h2safe_spatial_detector_transfer_validation", "hytunnel_carpark_dispersion_validation"}:
        return "공간좌표·방출방향·센서별 수치응답이 함께 있는 독립 holdout을 추가하고, 통과 전 runtime 자동 라우팅을 유지하지 않는다."
    if gate_id == "grune_2014_pressure_decay_validation":
        return (
            "공식 KIT·출판사 재확인에서도 권리 정리된 원시 pressure-time 표가 없어 1차 게이트는 보류 중이다. "
            "공개 ICHS 재현 도표의 figure-derived 진단은 완전 곡선을 제공하지만 세 고정 화면을 모두 통과하지 못했으므로 "
            "1차 근거로 승격하지 않는다. "
            "custodian 원자료와 재사용 조건을 받은 뒤 새 pre-access protocol을 동결한다. "
            "별도 KIT LH2 원자료는 공식 권리는 확인했지만 전체 아카이브 MD5가 검증되지 않아 "
            "이 게이트를 닫지 않는다."
        )
    if gate_id == "preslhy_blowdown_external_validation":
        return (
            "최초 동결 11/22(50.0%) 실패를 유지하고 16/22 사후 재실행은 개발 진단으로만 사용한다. "
            "밸브·배관 재고와 열전달을 포함한 후보 모델을 소비된 자료로 진단한 뒤 구현과 화면을 다시 동결하고, "
            "수치 결과를 열지 않은 독립 방출 캠페인에서 새 pre-access 프로토콜로 평가한다."
        )
    if gate_id in {"hytunnel_carpark_mass_flow_validation", "preslhy_partb_ambient_external_validation", "preslhy_revised_holdout_validation", "proust_independent_release_validation", "schefer_transient_release_validation", "schefer_2007_pressure_decay_validation", "grune_2014_pressure_decay_validation", "dickens_typeiii_prospective_validation"}:
        return "결과를 재튜닝하지 말고 실패한 물리량·직경·경계조건에 맞는 새 pre-access protocol과 독립 원시 trace를 확보한다."
    if gate_id == "institutional_ethics_determination":
        return (
            "선택 항목: SAGA가 운영자의 안전 판단을 개선한다고 주장할 때만 기관의 "
            "승인·면제·비대상 중 하나와 식별자를 확정하고 연구 기록에 보존한다."
        )
    if gate_id in {"hiad_casebook_frozen", "hiad_holdout_collection", "independent_expert_review_complete", "saga_effectiveness_and_safety_supported"}:
        return (
            "선택 항목: 사람 대상 SAGA 효과를 주장할 때만 고정된 HIAD 평가 프로토콜에 따라 "
            "casebook·응답·전문가 평가를 수집하고 freeze hash를 남긴다."
        )
    if gate_id == "submission_metadata_and_declarations":
        return "저자·기여·이해상충·자금·AI 사용 공개를 확인한 뒤 제출 메타데이터를 잠근다."
    return "게이트 정의와 독립 근거를 확인한 뒤 상태를 갱신한다."


def _claim_boundary(gate: dict[str, Any]) -> str:
    observed = gate.get("observed")
    if isinstance(observed, dict):
        boundary = observed.get("claim_boundary")
        if isinstance(boundary, str) and boundary:
            return boundary
        if observed.get("retained_negative_result"):
            return "실패 결과를 유지하며 해당 강한 주장은 현재 지원하지 않는다."
        if observed.get("full_loop_external_validation_supported") is False:
            return "완전한 충전소-차량 외부검증 주장은 현재 지원하지 않는다."
    if observed == "missing":
        return "증거 산출물이 없어 판정할 수 없다."
    return "현재 게이트 상태 이상의 주장은 허용하지 않는다."


def build_report(
    root: Path,
    *,
    audit_path: str = "research/ijhe_readiness_audit.json",
) -> dict[str, Any]:
    """Build the triage from an explicitly selected readiness snapshot.

    The default keeps backwards compatibility with the long-lived canonical
    audit path.  A dated audit can be selected for a current status report;
    silently reading an older snapshot would make the execution queue stale.
    """

    audit = _read(root, audit_path)
    gates = audit.get("gates") or []
    unresolved: list[dict[str, Any]] = []
    scope_exclusions: list[dict[str, Any]] = []
    for gate in gates:
        if not isinstance(gate, dict) or gate.get("status") not in {"FAIL", "PENDING"}:
            continue
        gate_id = str(gate.get("id", "unknown"))
        status = str(gate.get("status"))
        if gate_id in _FULL_LOOP:
            scope_exclusions.append(
                {
                    "id": gate_id,
                    "status": "OUT_OF_SCOPE",
                    "legacy_status": status,
                    "reason": (
                        "No reusable synchronized station-to-vehicle raw bundle was identified; "
                        "the current paper scope is station-side and component validation."
                    ),
                    "paper_limitation": (
                        "Do not claim independent station-to-vehicle full-loop accuracy, "
                        "vehicle-controller validation or field-safety validation."
                    ),
                    "reentry_condition": (
                        "A custodian provides rights-cleared synchronized station and vehicle "
                        "channels; then freeze a separate prospective protocol before scoring."
                    ),
                }
            )
            continue
        unresolved.append(
            {
                "id": gate_id,
                "status": status,
                "bucket": _bucket(gate_id),
                "priority": _TRACKS.get(_bucket(gate_id), {}).get("priority", "P3"),
                "parallel_track": _TRACKS.get(_bucket(gate_id), {}).get(
                    "parallel_track", "other"
                ),
                "scope_role": (
                    "optional_human_evaluation"
                    if gate_id in _OPTIONAL_HUMAN_EVALUATION
                    else "required_primary_scope"
                ),
                "claim": str(gate.get("claim", "")),
                "next_action": _next_action(gate_id, status),
                "why_now": _TRACKS.get(_bucket(gate_id), {}).get(
                    "why_now", "게이트 정의와 독립 근거를 먼저 확인"
                ),
                "claim_boundary": _claim_boundary(gate),
            }
        )

    unresolved.sort(key=lambda item: (item["priority"], item["id"]))

    by_bucket: dict[str, dict[str, int]] = {}
    for item in unresolved:
        bucket = item["bucket"]
        by_bucket.setdefault(bucket, {"FAIL": 0, "PENDING": 0})[item["status"]] += 1

    # Keep the legacy audit totals for traceability, but expose the declared
    # primary-scope metric beside them.  The full-loop station-to-vehicle lane
    # and the optional SAGA human-evaluation lane are deliberately excluded
    # from the active scope; showing only the legacy totals made the progress
    # report look inconsistent with the documented scope decision.
    excluded_from_primary_scope = {
        "full_loop_external_validation",
        "institutional_ethics_determination",
        "hiad_casebook_frozen",
        "hiad_holdout_collection",
        "independent_expert_review_complete",
        "saga_effectiveness_and_safety_supported",
        # Catalogue/file-access integrity is retained in the overall audit,
        # but is not a scientific validation gate for the declared scope.
        "public_nbsdc_lh2_station_intake_integrity",
    }
    scoped_gates = [
        gate for gate in gates
        if isinstance(gate, dict) and gate.get("id") not in excluded_from_primary_scope
    ]
    scoped_counts = {
        status: sum(gate.get("status") == status for gate in scoped_gates)
        for status in ("PASS", "FAIL", "PENDING")
    }
    scoped_total = sum(scoped_counts.values())
    scoped_closure = (
        scoped_counts["PASS"] / scoped_total * 100.0 if scoped_total else 0.0
    )

    target_journal = audit.get("target_journal") or {}
    # The readiness audit stores the journal display name under ``title``.
    # Keep a ``name`` fallback for older snapshots so the report never emits
    # a misleading null journal label.
    journal_name = target_journal.get("title") or target_journal.get("name")

    return {
        "schema_version": 1,
        "source_audit_generated_at": audit.get("generated_at"),
        "target_journal": journal_name,
        "overall": {
            "pass": (audit.get("gate_counts") or {}).get("PASS", 0),
            "fail": (audit.get("gate_counts") or {}).get("FAIL", 0),
            "pending": (audit.get("gate_counts") or {}).get("PENDING", 0),
            "full_user_objective_ready": bool(audit.get("full_user_objective_ready")),
        },
        "primary_scope": {
            "definition": (
                "Declared 2026-10-11 primary scope: station-side process/safety, "
                "public component holdouts and direct-answer SAGA grounding; "
                "full-loop, human-effectiveness and non-validation access-boundary "
                "checks remain excluded."
            ),
            "pass": scoped_counts["PASS"],
            "fail": scoped_counts["FAIL"],
            "pending": scoped_counts["PENDING"],
            "total": scoped_total,
            "closure_percent": round(scoped_closure, 1),
            "excluded_gate_ids": sorted(excluded_from_primary_scope),
        },
        "interpretation": {
            "data_volume_is_primary_blocker": False,
            "primary_blocker": "independent component-physics holdouts and protocol provenance",
            "rule": "FAIL은 실패한 주장을 유지하고, PENDING은 증거가 올 때까지 주장하지 않는다.",
            "privacy": "원시 행·경로·회사·사이트·제조사·달력 날짜를 이 보고서에 복사하지 않는다.",
        },
        "secondary_diagnostics": _secondary_diagnostics(root),
        "bucket_counts": by_bucket,
        "scope_exclusions": scope_exclusions,
        "execution_tracks": [
            {
                "priority": config["priority"],
                "parallel_track": config["parallel_track"],
                "bucket": bucket,
                "open_gate_count": sum(
                    1 for item in unresolved if item["bucket"] == bucket
                ),
                "why_now": config["why_now"],
            }
            for bucket, config in _TRACKS.items()
            if any(item["bucket"] == bucket for item in unresolved)
        ],
        "unresolved_gates": unresolved,
    }


def _markdown(report: dict[str, Any]) -> str:
    overall = report["overall"]
    scope = report.get("primary_scope") or {}
    lines = [
        "# Validation gap triage (privacy-bounded)",
        "",
        "현재 검증 게이트를 데이터 공백, 모델 공백, 검토 공백으로 분류한 의사결정용 보고서다. 새로운 수치 검증을 수행하거나 실패 게이트를 승격하지 않는다.",
        "",
        f"- PASS {overall['pass']} / FAIL {overall['fail']} / PENDING {overall['pending']}",
        (
            f"- 주 목표 범위: PASS {scope.get('pass', 0)} / "
            f"FAIL {scope.get('fail', 0)} / PENDING {scope.get('pending', 0)} "
            f"({scope.get('closure_percent', 0.0):.1f}%)"
        ),
        f"- 완전한 사용자 목표 준비 여부: {'예' if overall['full_user_objective_ready'] else '아니오'}",
        f"- 주된 병목: {report['interpretation']['primary_blocker']}",
        "",
    ]
    diagnostics = report.get("secondary_diagnostics") or []
    if diagnostics:
        diagnostic = diagnostics[0]
        lines.extend(
            [
                "## 1차 게이트에 반영하지 않은 보조 진단",
                "",
                (
                    "Grüne 사례에는 공개 ICHS 도표에서 추출한 완전 곡선 진단을 보존하지만, "
                    "권리 정리된 원시 아카이브가 아니며 고정 화면을 통과하지 못해 1차 검증을 닫지 않는다."
                ),
                (
                    f"- {diagnostic['points']} points · NRMSE "
                    f"{diagnostic['pressure_nrmse_percent_initial_measured']:.2f}% · "
                    f"median APE {diagnostic['median_absolute_percentage_error_percent']:.2f}% · "
                    f"half-pressure error {diagnostic['half_pressure_time_relative_error_percent']:.2f}%"
                ),
                "- 판정: DIAGNOSTIC_ONLY; 1차 게이트와 전체 진행률은 변경하지 않음",
                "",
            ]
        )
    lines.extend(
        [
        "## 미해결 게이트",
        "",
        "| 우선순위 | 병렬 트랙 | 게이트 | 상태 | 다음 최소 행동 |",
        "| --- | --- | --- | --- | --- |",
        ]
    )
    for item in report["unresolved_gates"]:
        lines.append(
            f"| {item['priority']} | {item['parallel_track']} | `{item['id']}` | "
            f"{item['status']} | {item['next_action']} |"
        )
    lines.extend(
        [
            "",
            "## 실행 순서",
            "",
            "- **P0** 현재 주 목표에 포함된 구성요소 물리 실패를 독립 holdout별로 병행합니다. 하나가 끝날 때까지 다른 트랙을 기다리지 않습니다.",
            "- **P1** 투고 메타데이터는 계산과 별도로 검토하고, 윤리·전문가 평가는 사람 대상 SAGA 효과 주장을 선택할 때만 시작합니다.",
            "- station-to-vehicle full-loop FAIL은 아래 범위 제외 목록에 보존하며, 현재 논문의 필수 작업 큐로 반복하지 않습니다.",
            "- 전체 회귀는 코드 변경이 있는 트랙에서만 실행하고, 상태 확인에는 이 보고서와 focused test만 사용합니다.",
            "",
            "## 사용 원칙",
            "",
            "- FAIL 결과는 모델을 맞추기 위해 재튜닝하지 않고 그대로 보존한다.",
            "- component 진단은 계속 사용할 수 있지만 full-loop·현장 안전거리·안전 인증으로 확장하지 않는다.",
            "- 원시 데이터를 공개하기 어려운 경우 custodian이 원시 파일을 보관하고, 비식별 이벤트와 해시·역할 증명·집계 지표만 전달한다.",
            "- 이 보고서는 회사·사이트·제조사·정확한 날짜·원시 경로를 포함하지 않는다.",
            "",
        ]
    )
    if report.get("scope_exclusions"):
        lines.extend(
            [
                "## 주 목표에서 제외한 게이트",
                "",
                "| 게이트 | 감사 상태 | 처리 |",
                "| --- | --- | --- |",
            ]
        )
        for item in report["scope_exclusions"]:
            lines.append(
                f"| `{item['id']}` | {item['legacy_status']} | {item['reason']} "
                f"논문 한계: {item['paper_limitation']} |"
            )
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument(
        "--audit",
        default="research/ijhe_readiness_audit.json",
        help="Readiness audit path relative to --root (supports dated snapshots).",
    )
    parser.add_argument("--json-output", type=Path, required=True)
    parser.add_argument("--markdown-output", type=Path, required=True)
    args = parser.parse_args()
    report = build_report(args.root.resolve(), audit_path=args.audit)
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_output.write_text(
        _markdown(report), encoding="utf-8", newline="\n"
    )
    print(args.json_output)
    print(args.markdown_output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
