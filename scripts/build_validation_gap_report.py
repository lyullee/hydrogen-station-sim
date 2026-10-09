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


def _read(root: Path, relative: str) -> dict[str, Any]:
    return json.loads((root / relative).read_text(encoding="utf-8"))


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
    if gate_id in {"hytunnel_carpark_mass_flow_validation", "preslhy_partb_ambient_external_validation", "preslhy_revised_holdout_validation", "proust_independent_release_validation", "schefer_transient_release_validation", "schefer_2007_pressure_decay_validation", "grune_2014_pressure_decay_validation", "dickens_typeiii_prospective_validation"}:
        return "결과를 재튜닝하지 말고 실패한 물리량·직경·경계조건에 맞는 새 pre-access protocol과 독립 원시 trace를 확보한다."
    if gate_id == "institutional_ethics_determination":
        return "기관의 승인·면제·비대상 중 하나와 식별자를 확정하고 연구 기록에 보존한다."
    if gate_id in {"hiad_casebook_frozen", "hiad_holdout_collection", "independent_expert_review_complete", "saga_effectiveness_and_safety_supported"}:
        return "고정된 HIAD 평가 프로토콜에 따라 casebook·응답·전문가 평가를 수집하고 freeze hash를 남긴다."
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


def build_report(root: Path) -> dict[str, Any]:
    audit = _read(root, "research/ijhe_readiness_audit.json")
    gates = audit.get("gates") or []
    unresolved: list[dict[str, Any]] = []
    for gate in gates:
        if not isinstance(gate, dict) or gate.get("status") not in {"FAIL", "PENDING"}:
            continue
        gate_id = str(gate.get("id", "unknown"))
        status = str(gate.get("status"))
        unresolved.append(
            {
                "id": gate_id,
                "status": status,
                "bucket": _bucket(gate_id),
                "claim": str(gate.get("claim", "")),
                "next_action": _next_action(gate_id, status),
                "claim_boundary": _claim_boundary(gate),
            }
        )

    by_bucket: dict[str, dict[str, int]] = {}
    for item in unresolved:
        bucket = item["bucket"]
        by_bucket.setdefault(bucket, {"FAIL": 0, "PENDING": 0})[item["status"]] += 1

    return {
        "schema_version": 1,
        "source_audit_generated_at": audit.get("generated_at"),
        "target_journal": audit.get("target_journal", {}).get("name"),
        "overall": {
            "pass": (audit.get("gate_counts") or {}).get("PASS", 0),
            "fail": (audit.get("gate_counts") or {}).get("FAIL", 0),
            "pending": (audit.get("gate_counts") or {}).get("PENDING", 0),
            "full_user_objective_ready": bool(audit.get("full_user_objective_ready")),
        },
        "interpretation": {
            "data_volume_is_primary_blocker": False,
            "primary_blocker": "synchronized receiving-vessel/controller channels and independent protocol provenance",
            "rule": "FAIL은 실패한 주장을 유지하고, PENDING은 증거가 올 때까지 주장하지 않는다.",
            "privacy": "원시 행·경로·회사·사이트·제조사·달력 날짜를 이 보고서에 복사하지 않는다.",
        },
        "bucket_counts": by_bucket,
        "unresolved_gates": unresolved,
    }


def _markdown(report: dict[str, Any]) -> str:
    overall = report["overall"]
    lines = [
        "# Validation gap triage (privacy-bounded)",
        "",
        "현재 검증 게이트를 데이터 공백, 모델 공백, 검토 공백으로 분류한 의사결정용 보고서다. 새로운 수치 검증을 수행하거나 실패 게이트를 승격하지 않는다.",
        "",
        f"- PASS {overall['pass']} / FAIL {overall['fail']} / PENDING {overall['pending']}",
        f"- 완전한 사용자 목표 준비 여부: {'예' if overall['full_user_objective_ready'] else '아니오'}",
        f"- 주된 병목: {report['interpretation']['primary_blocker']}",
        "",
        "## 미해결 게이트",
        "",
        "| 구분 | 게이트 | 상태 | 다음 최소 행동 |",
        "| --- | --- | --- | --- |",
    ]
    for item in report["unresolved_gates"]:
        lines.append(f"| {item['bucket']} | `{item['id']}` | {item['status']} | {item['next_action']} |")
    lines.extend(
        [
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
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--json-output", type=Path, required=True)
    parser.add_argument("--markdown-output", type=Path, required=True)
    args = parser.parse_args()
    report = build_report(args.root.resolve())
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_output.write_text(_markdown(report), encoding="utf-8")
    print(args.json_output)
    print(args.markdown_output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
