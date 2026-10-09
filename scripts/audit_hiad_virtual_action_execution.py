"""Audit public-incident response templates through virtual actuators.

The HIAD inventory provides public action categories, while the simulator
already exposes reviewed, executable response templates.  This audit joins
those two bounded artefacts and executes each physical family in the
simulation-only safety runtime.  It checks command acceptance, actuator
feedback and process-setting changes; it does not claim that a field operator
would choose the action correctly or that the action is effective in reality.
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from h2station.api import ProcessSettings  # noqa: E402
from h2station.operations import ProcessRuntime  # noqa: E402
from h2station.virtual_safety import suggested_actions  # noqa: E402


REPLAY = ROOT / "research/hiad_digital_twin_replay_coverage_2026_10_08.json"
PLAYBOOKS = ROOT / "src/h2station/data/emergency_playbooks.json"
ACTION_EVIDENCE = ROOT / "research/hiad_action_evidence.json"
SAFETY_RUNTIME = ROOT / "src/h2station/virtual_safety.py"
OUT_JSON = ROOT / "research/hiad_virtual_action_execution_2026_10_10.json"
OUT_MD = ROOT / "research/HIAD_VIRTUAL_ACTION_EXECUTION_2026_10_10.md"


# The node is the canonical simulator location used when the response plan is
# rendered in the UI.  These are deliberately representative locations, not
# inferred locations for the historical HIAD events.
FAMILY_NODES = {
    "gas_release": "N08",
    "hydrogen_fire": "N08",
    "hose_connection": "N13",
    "overpressure": "N08",
    "precooling_fault": "N12",
    "fueling_fault": "N11",
    "compressor_thermal": "N06",
    "external_fire": "N08",
    "isolation_failure": "N11",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _settings() -> ProcessSettings:
    # Start with every transfer path enabled so an operation.stop action has a
    # measurable before/after process-state effect.
    return ProcessSettings(
        trailer_supply=True,
        pressure_recharge=True,
        vehicle_1=True,
        vehicle_2=True,
    )


def _observe_valve(safety: Any, time_s: float) -> None:
    """Advance a commanded valve to feedback and confirm zero residual flow."""

    safety.tick(time_s + 0.5)
    safety.observe(
        time_s + 1.0,
        recharge_bank=None,
        dispatch_banks=(None, None),
        compressor_flow_g_s=0.0,
        dispenser_flows_g_s=(0.0, 0.0),
    )


def _run_family(family: str, node_id: str) -> dict[str, Any]:
    process = ProcessRuntime(_settings().model_dump())
    safety = process.safety
    before_settings = dict(process.snapshot()["settings"])
    templates = suggested_actions(family, node_id)
    rows: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    time_s = 0.0

    for template in templates:
        try:
            action = safety.issue(
                template["kind"], template["target"], time_s, process=process,
            )
            if template["kind"] == "valve.close":
                _observe_valve(safety, time_s)
                time_s += 1.0
            else:
                time_s += 0.01
            rows.append({
                "kind": template["kind"],
                "target": template["target"],
                "status": action["status"],
                "feedback_status": next(
                    (
                        item["status"]
                        for item in safety.snapshot()["actions"]
                        if item["id"] == action["id"]
                    ),
                    action["status"],
                ),
            })
        except Exception as exc:  # pragma: no cover - reported in artifact
            errors.append({
                "kind": template["kind"],
                "target": template["target"],
                "error": str(exc),
            })

    after_settings = dict(process.snapshot()["settings"])
    operation_keys = ("trailer_supply", "pressure_recharge", "vehicle_1", "vehicle_2")
    snapshot = safety.snapshot()
    closed_valves = sorted(
        name for name, valve in snapshot["valves"].items()
        if not name.startswith("vent.") and valve["actual_open"] is False
    )
    confirmed_count = sum(
        1 for row in snapshot["actions"]
        if row["kind"] != "fault.set" and row["status"] == "confirmed"
    )
    action_count = len(rows)
    process_changed = before_settings != after_settings
    return {
        "family": family,
        "representative_node_id": node_id,
        "status": "passed" if (
            bool(templates)
            and not errors
            and action_count == confirmed_count
            and process_changed
        ) else "failed",
        "checks": {
            "template_nonempty": bool(templates),
            "commands_accepted": not errors,
            "completion_feedback_confirmed": action_count == confirmed_count,
            "process_settings_changed": process_changed,
        },
        "action_count": action_count,
        "confirmed_action_count": confirmed_count,
        "actions": rows,
        "errors": errors,
        "closed_valves": closed_valves,
        "process_settings_before": {
            key: before_settings.get(key) for key in operation_keys
        },
        "process_settings_after": {
            key: after_settings.get(key) for key in operation_keys
        },
    }


def _failure_feedback_guard() -> dict[str, Any]:
    """Ensure a stuck-open valve is never reported as a successful closure."""

    process = ProcessRuntime(_settings().model_dump())
    safety = process.safety
    safety.set_fault("compressor.discharge", "stuck_open", 0.0)
    action = safety.issue("valve.close", "compressor.discharge", 0.0, process=process)
    _observe_valve(safety, 0.0)
    observed = safety.snapshot()["actions"][-1]
    return {
        "status": "passed" if observed["status"] == "failed" else "failed",
        "command_status": action["status"],
        "feedback_status": observed["status"],
        "fault": "stuck_open",
        "claim_limit": "가상 피드백 분리 회귀시험이며 실제 밸브 고장률이나 진단성능을 검증하지 않음",
    }


def build_audit() -> dict[str, Any]:
    replay = json.loads(REPLAY.read_text(encoding="utf-8"))
    families = {
        str(family): row
        for family, row in (replay.get("family_recipes") or {}).items()
        if str(family) in FAMILY_NODES and row.get("status") == "passed"
    }
    results = {
        family: _run_family(family, FAMILY_NODES[family])
        for family in sorted(families)
    }
    failed_feedback = _failure_feedback_guard()
    passed = sum(row["status"] == "passed" for row in results.values())
    action_count = sum(int(row["action_count"]) for row in results.values())
    return {
        "schema_version": 1,
        "artifact_type": "hiad_virtual_response_action_execution_consistency_audit",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "completed_virtual_action_execution_audit",
        "evidence_role": "public_action_category_to_simulation_command_consistency_only",
        "source": {
            "hiad_replay_coverage": str(REPLAY.relative_to(ROOT)).replace("\\", "/"),
            "hiad_replay_coverage_sha256": _sha256(REPLAY),
            "action_evidence": str(ACTION_EVIDENCE.relative_to(ROOT)).replace("\\", "/"),
            "action_evidence_sha256": _sha256(ACTION_EVIDENCE),
            "playbook_catalog": str(PLAYBOOKS.relative_to(ROOT)).replace("\\", "/"),
            "playbook_catalog_sha256": _sha256(PLAYBOOKS),
            "virtual_safety_runtime": str(SAFETY_RUNTIME.relative_to(ROOT)).replace("\\", "/"),
            "virtual_safety_runtime_sha256": _sha256(SAFETY_RUNTIME),
        },
        "runtime": {
            "family_count": len(results),
            "family_pass_count": passed,
            "action_count": action_count,
            "all_family_sequences_passed": passed == len(results),
            "failure_feedback_guard": failed_feedback,
        },
        "family_results": results,
        "excluded_response_only_families": sorted(
            set((replay.get("family_recipes") or {})) - set(FAMILY_NODES)
        ),
        "claim_boundary": [
            "Each sequence is a simulation-only command/feedback replay using representative node IDs; it is not a reconstruction of a historical HIAD event.",
            "A pass means the registered template is accepted by the virtual runtime, changes the requested process/safety state, and reports completion feedback.",
            "The stuck-open check confirms command and feedback are kept separate; it does not estimate field valve reliability or diagnostic sensitivity.",
            "No operator benefit, LLM effectiveness, accident frequency, consequence distance or field safety claim is made.",
            "Structural damage remains excluded because the current process model has no structural mechanics.",
        ],
    }


def write_outputs(result: dict[str, Any]) -> None:
    OUT_JSON.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8", newline="\n",
    )
    runtime = result["runtime"]
    lines = [
        "# HIAD virtual response-action execution consistency",
        "",
        "공개 사고자료에서 추출한 조치 범주를 대표 가상 시나리오의 안전명령으로 연결하고,",
        "명령 수락·피드백·공정상태 변화까지 확인한 시뮬레이션 전용 회귀검사입니다.",
        "",
        f"- 실행 가능한 response family: **{runtime['family_count']}**",
        f"- family 통과: **{runtime['family_pass_count']}/{runtime['family_count']}**",
        f"- 실행 명령 수: **{runtime['action_count']}**",
        f"- 피드백 고장 분리 검사: **{runtime['failure_feedback_guard']['status']}**",
        "",
        "| Family | 대표 노드 | 명령 수 | 피드백 | 상태 |",
        "|---|---|---:|---|---|",
    ]
    for family, row in result["family_results"].items():
        lines.append(
            f"| `{family}` | `{row['representative_node_id']}` | "
            f"{row['action_count']} | {row['confirmed_action_count']}/{row['action_count']} | "
            f"`{row['status']}` |"
        )
    lines += ["", "## Claim boundary", "", *[f"- {item}" for item in result["claim_boundary"]], ""]
    OUT_MD.write_text("\n".join(lines), encoding="utf-8", newline="\n")


def main() -> int:
    result = build_audit()
    write_outputs(result)
    print(json.dumps(result["runtime"], ensure_ascii=False, indent=2))
    return 0 if (
        result["runtime"]["all_family_sequences_passed"]
        and result["runtime"]["failure_feedback_guard"]["status"] == "passed"
    ) else 1


if __name__ == "__main__":
    raise SystemExit(main())
