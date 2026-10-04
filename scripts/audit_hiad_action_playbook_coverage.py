"""Audit traceability from public HIAD action categories to response plans.

This is a provenance and coverage audit only.  It does not judge whether an
incident action was safe, does not estimate incident probabilities, and does
not evaluate an LLM.  The result is deliberately kept separate from the
blinded HIAD decision holdout.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ACTION_EVIDENCE = ROOT / "research/hiad_action_evidence.json"
PLAYBOOKS = ROOT / "src/h2station/data/emergency_playbooks.json"
OUTPUT = ROOT / "research/hiad_action_playbook_coverage.json"
MARKDOWN = ROOT / "research/HIAD_ACTION_PLAYBOOK_COVERAGE.md"

# Controlled crosswalk reviewed as a data contract.  A category is covered
# when at least one plan exposes the response stages used by the simulator.
CATEGORY_TO_PLANS = {
    "shutdown_isolation_depressurization": [
        "gas_release", "hydrogen_fire", "external_fire", "overpressure",
        "relief_discharge", "fueling_fault", "hose_connection",
        "compressor_thermal", "precooling_fault", "flow_anomaly",
        "isolation_failure", "supply_connection",
    ],
    "detection_alarm_monitoring": [
        "gas_release", "hydrogen_fire", "external_fire", "overpressure",
        "relief_discharge", "flow_anomaly", "sensor_fault",
    ],
    "fire_response_cooling": ["hydrogen_fire", "external_fire"],
    "evacuation_perimeter_access": [
        "gas_release", "hydrogen_fire", "external_fire", "relief_discharge",
        "overpressure",
    ],
    "emergency_communication_coordination": [
        "gas_release", "hydrogen_fire", "external_fire", "overpressure",
        "relief_discharge", "fueling_fault", "hose_connection",
    ],
    "inspection_leak_test_repair": [
        "gas_release", "relief_discharge", "hose_connection", "sensor_fault",
        "isolation_failure", "supply_connection", "structural_damage",
        "compressor_thermal", "precooling_fault",
    ],
    "procedure_interlock_training_design": [
        "gas_release", "hydrogen_fire", "external_fire", "overpressure",
        "relief_discharge", "fueling_fault", "hose_connection",
        "compressor_thermal", "precooling_fault", "structural_damage",
        "flow_anomaly", "low_supply_or_blockage", "vent_fault", "sensor_fault",
        "isolation_failure", "supply_connection",
    ],
    "ventilation_purge": [
        "gas_release", "hydrogen_fire", "relief_discharge",
        "low_supply_or_blockage", "vent_fault",
    ],
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def audit(root: Path = ROOT) -> dict:
    evidence_path = root / ACTION_EVIDENCE.relative_to(ROOT)
    playbook_path = root / PLAYBOOKS.relative_to(ROOT)
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    playbooks = json.loads(playbook_path.read_text(encoding="utf-8"))
    plans = {str(item.get("id")): item for item in playbooks.get("plans", [])}
    categories = sorted((evidence.get("taxonomy") or {}).get("category_counts", {}))

    category_rows = []
    missing_plan_ids = set()
    incomplete_plan_ids = set()
    for category in categories:
        plan_ids = CATEGORY_TO_PLANS.get(category, [])
        missing = [plan_id for plan_id in plan_ids if plan_id not in plans]
        missing_plan_ids.update(missing)
        incomplete = [
            plan_id for plan_id in plan_ids
            if plan_id in plans and any(not plans[plan_id].get(stage) for stage in (
                "recognition", "immediate", "stabilize", "restart", "prevention"
            ))
        ]
        incomplete_plan_ids.update(incomplete)
        category_rows.append({
            "category": category,
            "incident_count": int((evidence.get("taxonomy") or {}).get("category_counts", {}).get(category, 0)),
            "mapped_plan_ids": plan_ids,
            "mapped_plan_count": len(plan_ids),
            "missing_plan_ids": missing,
            "all_mapped_plans_have_five_stages": not incomplete,
            "covered": bool(plan_ids) and not missing and not incomplete,
        })

    case_rows = []
    for case in evidence.get("cases", []):
        case_categories = [str(item) for item in case.get("action_categories", [])]
        unresolved = [item for item in case_categories if not any(
            row["category"] == item and row["covered"] for row in category_rows
        )]
        case_rows.append({
            "event_id": str(case.get("event_id")),
            "action_category_count": len(case_categories),
            "unresolved_categories": unresolved,
            "covered": not unresolved,
        })

    covered_categories = sum(bool(row["covered"]) for row in category_rows)
    covered_cases = sum(bool(row["covered"]) for row in case_rows)
    report = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "completed_public_action_to_playbook_traceability_audit",
        "evidence_role": "public_incident_grounding_traceability_only",
        "source": {
            "action_evidence_path": str(evidence_path.relative_to(root)),
            "action_evidence_sha256": _sha256(evidence_path),
            "playbook_path": str(playbook_path.relative_to(root)),
            "playbook_sha256": _sha256(playbook_path),
            "case_count": len(case_rows),
            "category_count": len(category_rows),
        },
        "aggregate": {
            "category_count": len(category_rows),
            "covered_category_count": covered_categories,
            "category_coverage_fraction": covered_categories / len(category_rows) if category_rows else 0.0,
            "case_count": len(case_rows),
            "covered_case_count": covered_cases,
            "case_coverage_fraction": covered_cases / len(case_rows) if case_rows else 0.0,
            "missing_plan_ids": sorted(missing_plan_ids),
            "incomplete_plan_ids": sorted(incomplete_plan_ids),
            "contract_pass": bool(
                category_rows
                and covered_categories == len(category_rows)
                and case_rows
                and covered_cases == len(case_rows)
            ),
        },
        "categories": category_rows,
        "cases": case_rows,
        "crosswalk": CATEGORY_TO_PLANS,
        "claim_boundary": (
            "This audit verifies only that public HIAD action categories have a "
            "traceable five-stage response plan in the simulator. It does not "
            "judge incident actions, validate physics, estimate probabilities, "
            "or evaluate SAGA/LLM effectiveness or safety. The records remain "
            "excluded from the blinded HIAD holdout."
        ),
    }
    return report


def _markdown(report: dict) -> str:
    aggregate = report["aggregate"]
    lines = [
        "# HIAD Action-to-Playbook Coverage Audit",
        "",
        "이 문서는 공개 HIAD 조치 범주와 시뮬레이터 대응계획의 추적성만 검사합니다.",
        "사고 조치의 옳고 그름, 물리 검증, 확률, LLM 효능은 평가하지 않습니다.",
        "",
        f"- 사고 사례: **{aggregate['case_count']}**",
        f"- 조치 범주: **{aggregate['covered_category_count']}/{aggregate['category_count']}**",
        f"- 사례 연결: **{aggregate['covered_case_count']}/{aggregate['case_count']}**",
        f"- 계약 통과: **{aggregate['contract_pass']}**",
        "",
        "| 조치 범주 | 사례 수 | 연결 계획 수 | 단계 완비 |",
        "|---|---:|---:|:---:|",
    ]
    for row in report["categories"]:
        lines.append(
            f"| `{row['category']}` | {row['incident_count']} | "
            f"{row['mapped_plan_count']} | {'예' if row['covered'] else '아니오'} |"
        )
    lines.extend(["", report["claim_boundary"], ""])
    return "\n".join(lines)


def main() -> int:
    report = audit()
    OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    MARKDOWN.write_text(_markdown(report), encoding="utf-8")
    print(json.dumps(report["aggregate"], ensure_ascii=False))
    return 0 if report["aggregate"]["contract_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
