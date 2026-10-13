"""Evaluate public HIAD action-category coverage in staged response plans.

This is a deterministic, non-evaluative traceability check.  It joins the
controlled action categories derived from the public HIAD workbook to the
candidate response families already selected from each case's public
metadata, then checks that the stages required by each category are present.
It deliberately does not retain HIAD prose, score incident actions, validate
physics, or claim that an operator or an LLM is effective or safe.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from h2station.virtual_safety import suggested_actions  # noqa: E402


ACTION_EVIDENCE = ROOT / "research/hiad_action_evidence.json"
STAGE_CONTRACT = ROOT / "research/hiad_response_stage_contract.json"
PLAYBOOK_COVERAGE = ROOT / "research/hiad_action_playbook_coverage.json"
PLAYBOOKS = ROOT / "src/h2station/data/emergency_playbooks.json"
VIRTUAL_SAFETY = ROOT / "src/h2station/virtual_safety.py"
OUTPUT = ROOT / "research/hiad_accident_response_coverage_evaluation_2026_10_05.json"
MARKDOWN = ROOT / "research/HIAD_ACCIDENT_RESPONSE_COVERAGE_EVALUATION.md"

STAGES = ("recognition", "immediate", "stabilize", "restart", "prevention")

# This crosswalk is a simulator interface contract.  The stage choices are
# deliberately conservative minimums for presenting an action category; they
# are not a claim that the HIAD source prescribed these exact steps.
CATEGORY_REQUIRED_STAGES = {
    "shutdown_isolation_depressurization": ("immediate", "stabilize", "restart"),
    "detection_alarm_monitoring": ("recognition", "stabilize", "prevention"),
    "fire_response_cooling": ("immediate", "stabilize", "prevention"),
    "evacuation_perimeter_access": ("immediate", "stabilize"),
    "emergency_communication_coordination": ("immediate", "prevention"),
    "inspection_leak_test_repair": ("restart", "prevention"),
    "procedure_interlock_training_design": ("prevention",),
    "ventilation_purge": ("immediate", "stabilize", "prevention"),
}

# Only categories that translate into an immediate virtual control or
# coordination command are required to expose an executable action.  The
# remaining categories are monitoring, recovery or lifecycle obligations and
# continue to use the staged-plan contract.  This is interface traceability,
# not evidence that an action is correct or effective in a real facility.
CATEGORY_EXECUTION_CONTRACT = {
    "shutdown_isolation_depressurization": {
        "mode": "virtual_command_required",
        "accepted_action_kinds": ("operation.stop", "valve.close", "esd.trip", "vent.open"),
    },
    "detection_alarm_monitoring": {
        "mode": "staged_workflow_only",
        "accepted_action_kinds": (),
    },
    "fire_response_cooling": {
        "mode": "virtual_command_required",
        "accepted_action_kinds": ("cooling.on", "operation.stop", "valve.close", "esd.trip"),
    },
    "evacuation_perimeter_access": {
        "mode": "virtual_command_required",
        "accepted_action_kinds": ("personnel.evacuate", "access.restrict", "vehicle.evacuate"),
    },
    "emergency_communication_coordination": {
        "mode": "virtual_command_required",
        "accepted_action_kinds": ("responders.notify",),
    },
    "inspection_leak_test_repair": {
        "mode": "staged_workflow_only",
        "accepted_action_kinds": (),
    },
    "procedure_interlock_training_design": {
        "mode": "staged_workflow_only",
        "accepted_action_kinds": (),
    },
    "ventilation_purge": {
        "mode": "virtual_command_required",
        "accepted_action_kinds": ("ventilation.on", "purge.run"),
    },
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _plan_stage_ok(plan: dict, required: tuple[str, ...]) -> bool:
    return all(
        isinstance(plan.get(stage), list)
        and bool(plan.get(stage))
        and all(str(item).strip() for item in plan.get(stage, []))
        for stage in required
    )


def evaluate(root: Path = ROOT) -> dict:
    action_path = root / ACTION_EVIDENCE.relative_to(ROOT)
    stage_path = root / STAGE_CONTRACT.relative_to(ROOT)
    coverage_path = root / PLAYBOOK_COVERAGE.relative_to(ROOT)
    playbook_path = root / PLAYBOOKS.relative_to(ROOT)

    action = json.loads(action_path.read_text(encoding="utf-8"))
    stage_contract = json.loads(stage_path.read_text(encoding="utf-8"))
    action_coverage = json.loads(coverage_path.read_text(encoding="utf-8"))
    playbook_catalog = json.loads(playbook_path.read_text(encoding="utf-8"))
    plans = {str(plan["id"]): plan for plan in playbook_catalog.get("plans", [])}
    stage_cases = {str(row["event_id"]): row for row in stage_contract.get("cases", [])}

    action_cases = {str(row["event_id"]): row for row in action.get("cases", [])}
    coverage_cases = {str(row["event_id"]): row for row in action_coverage.get("cases", [])}
    category_counts = {
        str(key): int(value)
        for key, value in (action.get("taxonomy") or {}).get("category_counts", {}).items()
    }

    case_rows: list[dict[str, object]] = []
    uncovered: list[dict[str, object]] = []
    category_case_counts: Counter[str] = Counter()
    category_covered_counts: Counter[str] = Counter()
    category_executable_counts: Counter[str] = Counter()
    category_stage_obligations: dict[str, dict[str, object]] = {}
    executable_uncovered: list[dict[str, object]] = []

    for event_id, case in action_cases.items():
        categories = [str(item) for item in case.get("action_categories", [])]
        stage_row = stage_cases.get(event_id, {})
        candidate_plan_ids = [str(item) for item in stage_row.get("candidate_plan_ids", [])]
        registered_plan_ids = [plan_id for plan_id in candidate_plan_ids if plan_id in plans]
        coverage_row = coverage_cases.get(event_id, {})
        category_results: list[dict[str, object]] = []

        for category in categories:
            required = tuple(CATEGORY_REQUIRED_STAGES.get(category, STAGES))
            execution_contract = CATEGORY_EXECUTION_CONTRACT.get(category, {
                "mode": "staged_workflow_only", "accepted_action_kinds": (),
            })
            accepted_action_kinds = set(execution_contract["accepted_action_kinds"])
            category_case_counts[category] += 1
            eligible_plan_ids = [
                plan_id for plan_id in registered_plan_ids
                if _plan_stage_ok(plans[plan_id], required)
            ]
            plan_actions = {
                plan_id: suggested_actions(plan_id)
                for plan_id in registered_plan_ids
            }
            executable_plan_ids = [
                plan_id for plan_id, actions in plan_actions.items()
                if accepted_action_kinds.intersection(
                    str(action.get("kind", "")) for action in actions
                )
            ]
            executable_required = execution_contract["mode"] == "virtual_command_required"
            executable_covered = bool(executable_plan_ids) if executable_required else None
            stage_covered = bool(eligible_plan_ids)
            covered = stage_covered and (executable_covered is not False)
            if covered:
                category_covered_counts[category] += 1
            else:
                uncovered.append({
                    "event_id": event_id,
                    "category": category,
                    "candidate_plan_ids": candidate_plan_ids,
                    "required_stages": list(required),
                })
            if executable_required:
                if executable_covered:
                    category_executable_counts[category] += 1
                else:
                    executable_uncovered.append({
                        "event_id": event_id,
                        "category": category,
                        "candidate_plan_ids": candidate_plan_ids,
                        "accepted_action_kinds": sorted(accepted_action_kinds),
                    })
            category_stage_obligations.setdefault(category, {
                "required_stages": list(required),
                "rationale": "minimum interface stages for presenting this public action category; not a source-action correctness claim",
            })
            category_results.append({
                "category": category,
                "required_stages": list(required),
                "covering_plan_ids": eligible_plan_ids,
                "execution_requirement": execution_contract["mode"],
                "accepted_action_kinds": sorted(accepted_action_kinds),
                "executable_plan_ids": executable_plan_ids,
                "executable_covered": executable_covered,
                "covered": covered,
            })

        no_public_category = not categories
        case_rows.append({
            "event_id": event_id,
            "title": str(case.get("title", "")),
            "physical_effect": str(case.get("physical_effect", "")),
            "action_category_count": len(categories),
            "action_categories": categories,
            "candidate_plan_ids": candidate_plan_ids,
            "registered_candidate_plan_ids": registered_plan_ids,
            "stage_contract": stage_row.get("stage_contract"),
            "action_traceability_status": (
                "not_assessed_no_public_category" if no_public_category
                else "covered" if all(item["covered"] for item in category_results)
                else "uncovered"
            ),
            "category_results": category_results,
            "public_category_text_used": False,
            "holdout_use": False,
            "coverage_source_row_status": coverage_row.get("coverage_status"),
        })

    action_category_case_count = sum(bool(row["action_categories"]) for row in case_rows)
    covered_action_category_case_count = sum(
        row["action_traceability_status"] == "covered" for row in case_rows
    )
    category_rows = []
    for category in sorted(CATEGORY_REQUIRED_STAGES):
        expected = category_counts.get(category, 0)
        assessed = category_case_counts.get(category, 0)
        covered = category_covered_counts.get(category, 0)
        execution_contract = CATEGORY_EXECUTION_CONTRACT[category]
        executable_required = execution_contract["mode"] == "virtual_command_required"
        executable_covered = category_executable_counts.get(category, 0)
        category_rows.append({
            "category": category,
            "public_case_count": expected,
            "assessed_case_count": assessed,
            "covered_case_count": covered,
            "uncovered_case_count": assessed - covered,
            "required_stages": list(CATEGORY_REQUIRED_STAGES[category]),
            "execution_requirement": execution_contract["mode"],
            "accepted_action_kinds": list(execution_contract["accepted_action_kinds"]),
            "executable_covered_case_count": executable_covered if executable_required else None,
            "executable_uncovered_case_count": (
                assessed - executable_covered if executable_required else None
            ),
            "coverage_fraction": covered / assessed if assessed else None,
            "category_present_in_source_taxonomy": category in category_counts,
        })

    source_hashes = {
        "action_evidence_sha256": _sha256(action_path),
        "response_stage_contract_sha256": _sha256(stage_path),
        "action_playbook_coverage_sha256": _sha256(coverage_path),
        "playbook_catalog_sha256": _sha256(playbook_path),
        "virtual_safety_runtime_sha256": _sha256(root / VIRTUAL_SAFETY.relative_to(ROOT)),
    }
    source_hash_matches = (
        (action.get("source") or {}).get("sha256")
        == _sha256(root / str((action.get("source") or {}).get("path", "")))
        if (action.get("source") or {}).get("path") else False
    )
    contract_pass = bool(
        len(case_rows) == 34
        and action_category_case_count == 33
        and len(category_rows) == 8
        and all(row["public_case_count"] == row["assessed_case_count"] for row in category_rows)
        and all(row["uncovered_case_count"] == 0 for row in category_rows)
        and covered_action_category_case_count == action_category_case_count
        and not uncovered
        and not executable_uncovered
        and all(row["stage_contract"] == "pass" for row in case_rows)
        and all(row["registered_candidate_plan_ids"] for row in case_rows)
        and source_hash_matches
        and (action.get("source") or {}).get("raw_text_retained") is False
        and (action.get("source") or {}).get("holdout_use") is False
    )

    return {
        "schema_version": 2,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "completed_public_accident_response_coverage_evaluation",
        "evidence_role": "public_accident_grounded_interface_evaluation",
        "source": {
            "action_evidence": "research/hiad_action_evidence.json",
            "response_stage_contract": "research/hiad_response_stage_contract.json",
            "action_playbook_coverage": "research/hiad_action_playbook_coverage.json",
            "playbook_catalog": "src/h2station/data/emergency_playbooks.json",
            "virtual_safety_runtime": "src/h2station/virtual_safety.py",
            "hashes": source_hashes,
            "action_evidence_source_hash_matches": source_hash_matches,
        },
        "contract": {
            "required_stage_names": list(STAGES),
            "category_required_stages": category_stage_obligations,
            "category_execution_contract": CATEGORY_EXECUTION_CONTRACT,
            "virtual_actions_are_simulation_only": True,
            "external_notification_performed": False,
            "raw_action_text_used": False,
            "effectiveness_claimed": False,
            "safety_claimed": False,
            "holdout_use": False,
        },
        "aggregate": {
            "case_count": len(case_rows),
            "public_action_category_case_count": action_category_case_count,
            "no_public_action_category_case_count": len(case_rows) - action_category_case_count,
            "covered_action_category_case_count": covered_action_category_case_count,
            "category_count": len(category_rows),
            "covered_category_count": sum(row["uncovered_case_count"] == 0 for row in category_rows),
            "uncovered_case_category_count": len(uncovered),
            "active_action_category_count": sum(
                row["execution_requirement"] == "virtual_command_required"
                for row in category_rows
            ),
            "executable_case_category_count": sum(
                int(row["assessed_case_count"])
                for row in category_rows
                if row["execution_requirement"] == "virtual_command_required"
            ),
            "executable_uncovered_case_category_count": len(executable_uncovered),
            "category_counts": category_counts,
            "contract_pass": contract_pass,
        },
        "categories": category_rows,
        "cases": case_rows,
        "uncovered": uncovered,
        "executable_uncovered": executable_uncovered,
        "claim_boundary": (
            "This artifact shows only that action categories derived from public HIAD "
            "metadata can be routed to registered staged response plans and that active "
            "response categories expose at least one simulation-only command. Virtual "
            "responder notification never contacts an external service. A case with "
            "no recorded public category is not treated as having no response. The "
            "result does not judge source actions, validate physics, estimate risk, "
            "or demonstrate SAGA/LLM/operator effectiveness or safety. Independent "
            "expert review and blinded holdout testing remain required."
        ),
    }


def _markdown(report: dict) -> str:
    aggregate = report["aggregate"]
    lines = [
        "# HIAD accident-response coverage evaluation",
        "",
        "공개 HIAD 원자료의 조치 문장을 재배포하지 않고, 통제된 조치 범주를 시스템의 단계별 대응계획으로 라우팅할 수 있는지 검사한 결과입니다.",
        "이 결과는 조치의 정확성·안전성·효과성이나 LLM의 성능을 검증하지 않습니다.",
        "",
        f"- 상태: **{'PASS' if aggregate['contract_pass'] else 'FAIL'}**",
        f"- 전체 사례: **{aggregate['case_count']}**",
        f"- 공개 조치 범주가 기록된 사례: **{aggregate['public_action_category_case_count']}**",
        f"- 범주가 기록되지 않은 사례: **{aggregate['no_public_action_category_case_count']}** (대응 없음으로 해석하지 않음)",
        f"- 범주 커버리지: **{aggregate['covered_category_count']}/{aggregate['category_count']}**",
        f"- 미커버 사례-범주 쌍: **{aggregate['uncovered_case_category_count']}**",
        f"- 실행명령 필수 범주: **{aggregate['active_action_category_count']}**",
        f"- 실행명령 미커버 사례-범주 쌍: **{aggregate['executable_uncovered_case_category_count']}**",
        "",
        "## 범주별 단계 계약",
        "",
        "| 공개 조치 범주 | 사례 수 | 커버 사례 | 실행 계약 | 실행 미커버 | 필수 단계 |",
        "|---|---:|---:|---|---:|---|",
    ]
    for row in report["categories"]:
        lines.append(
            f"| `{row['category']}` | {row['assessed_case_count']} | "
            f"{row['covered_case_count']} | `{row['execution_requirement']}` | "
            f"{row['executable_uncovered_case_count'] if row['executable_uncovered_case_count'] is not None else '해당 없음'} | "
            f"{', '.join(row['required_stages'])} |"
        )
    lines.extend([
        "",
        "## 해석 경계",
        "",
        report["claim_boundary"],
        "",
        "입력 해시:",
        "",
    ])
    for key, value in report["source"]["hashes"].items():
        lines.append(f"- `{key}`: `{value}`")
    return "\n".join(lines) + "\n"


def main() -> int:
    report = evaluate()
    OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    MARKDOWN.write_text(_markdown(report), encoding="utf-8", newline="\n")
    print(json.dumps(report["aggregate"], ensure_ascii=False, indent=2))
    return 0 if report["aggregate"]["contract_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
