"""Audit HIAD family fixtures through the runtime response handoff.

The public HIAD inventory is retrospective metadata.  This audit does not
reconstruct an incident.  It executes one declared canonical fixture per
mapped family and verifies that the resulting monitor frame is converted into
the expected response family and complete staged guidance.  The purpose is to
catch integration regressions such as an ignited hydrogen release being
described as an unignited leak only.
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
sys.path.insert(0, str(ROOT / "scripts"))

from audit_hiad_digital_twin_replay_coverage import (  # noqa: E402
    _recipe_catalog,
    _run_scenario,
)
from h2station.hazop.database import load_catalog  # noqa: E402
from h2station.hazop.response import (  # noqa: E402
    response_selection,
    structured_guidance,
)


REPLAY_ARTIFACT = ROOT / "research/hiad_digital_twin_replay_coverage_2026_10_08.json"
RESPONSE_MODULE = ROOT / "src/h2station/hazop/response.py"
PLAYBOOKS = ROOT / "src/h2station/data/emergency_playbooks.json"
OUT_JSON = ROOT / "research/hiad_runtime_response_handoff_2026_10_09.json"
OUT_MD = ROOT / "research/HIAD_RUNTIME_RESPONSE_HANDOFF_2026_10_09.md"

EXPECTED_PLANS: dict[str, tuple[str, ...]] = {
    "gas_release": ("gas_release",),
    "hydrogen_fire": ("hydrogen_fire",),
    "hose_connection": ("gas_release",),
    "overpressure": ("overpressure",),
    "precooling_fault": ("precooling_fault",),
    "fueling_fault": ("low_supply_or_blockage",),
    "compressor_thermal": ("external_fire",),
    "external_fire": ("external_fire",),
    "isolation_failure": ("fueling_fault", "low_supply_or_blockage"),
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _run_handoff(family: str, recipe: dict[str, Any], catalog: dict[str, Any]) -> dict[str, Any]:
    event = recipe["event"]
    duration_s = float(recipe["duration_s"])
    _, monitor = _run_scenario(event, duration_s)
    frame = monitor.frames[-1] if monitor.frames else {}
    # The live API uses the same string representation for active fault
    # context.  The monitor frame remains the source of detector, HAZOP and
    # consequence evidence.
    active_faults = []
    if event is not None:
        active_faults.append(f"{event.kind.value}:{event.target}")
    runtime_frame = {
        "hazop": frame,
        "active_faults": active_faults,
    }
    selected = response_selection(runtime_frame, catalog, trigger="alarm")
    guidance = structured_guidance(selected, actual_alert=True)
    selected_ids = [str(item["plan"]["id"]) for item in selected]
    expected = set(EXPECTED_PLANS.get(family, ()))
    selected_set = set(selected_ids)
    expected_present = expected.issubset(selected_set)
    guidance_plans = (guidance or {}).get("plans") or []
    guidance_ids = {str(plan.get("id")) for plan in guidance_plans}
    stages_complete = bool(guidance and guidance.get("actual_alert")) and all(
        all(plan.get(stage) for stage in
            ("recognition", "immediate", "stabilize", "restart", "prevention"))
        for plan in guidance_plans
    )
    handoff_pass = bool(selected_ids) and expected_present and expected.issubset(guidance_ids) and stages_complete
    consequence_rows = frame.get("releases") or []
    return {
        "family": family,
        "status": "passed" if handoff_pass else "failed",
        "event_kind": event.kind.value if event is not None else None,
        "event_target": event.target if event is not None else None,
        "active_fault_context": active_faults,
        "selected_plan_ids": selected_ids,
        "expected_plan_ids": sorted(expected),
        "guidance_plan_ids": sorted(guidance_ids),
        "checks": {
            "monitor_frame_available": bool(frame),
            "response_selection_nonempty": bool(selected_ids),
            "expected_plan_selected": expected_present,
            "structured_guidance_available": guidance is not None,
            "staged_guidance_complete": stages_complete,
            "consequence_evidence_present": bool(consequence_rows),
        },
        "observed": {
            "monitor_frame_time_s": frame.get("time_s"),
            "active_rule_count": len(frame.get("active") or []),
            "release_count": len(consequence_rows),
            "release_ids": sorted(str(row.get("release_id")) for row in consequence_rows),
            "active_sensor_ids": sorted(str(row.get("sensor_id")) for row in frame.get("active") or []),
        },
        "claim_boundary": (
            "A passed handoff proves only that the canonical fixture reaches the "
            "registered response family and five staged guidance fields. It does "
            "not prove accident reconstruction, response effectiveness, frequency "
            "or a safe-distance value."
        ),
    }


def build_audit() -> dict[str, Any]:
    catalog = load_catalog()
    recipes = _recipe_catalog()
    results: dict[str, dict[str, Any]] = {}
    for family, recipe in recipes.items():
        if recipe["event"] is None:
            continue
        results[family] = _run_handoff(family, recipe, catalog)
    passed = sum(row["status"] == "passed" for row in results.values())
    return {
        "schema_version": 1,
        "artifact_type": "hiad_runtime_response_handoff_audit",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "completed_canonical_family_handoff_audit",
        "evidence_role": "retrospective_metadata_to_runtime_response_traceability_only",
        "source": {
            "replay_coverage_artifact": str(REPLAY_ARTIFACT.relative_to(ROOT)).replace("\\", "/"),
            "replay_coverage_artifact_sha256": _sha256(REPLAY_ARTIFACT),
            "response_module": str(RESPONSE_MODULE.relative_to(ROOT)).replace("\\", "/"),
            "response_module_sha256": _sha256(RESPONSE_MODULE),
            "playbook_catalog": str(PLAYBOOKS.relative_to(ROOT)).replace("\\", "/"),
            "playbook_catalog_sha256": _sha256(PLAYBOOKS),
        },
        "runtime": {
            "backend": "HyRAM+ 6.1 native",
            "virtual_detector_mode": True,
            "unique_family_recipes_run": len(results),
            "response_handoff_pass_count": passed,
            "all_executable_handoffs_passed": passed == len(results),
        },
        "family_results": results,
        "claim_boundary": [
            "The public HIAD inventory does not provide synchronized boundary traces; canonical fixtures are used for runtime testing.",
            "The audit checks monitor-frame availability, response-family selection, structured guidance and complete recognition/immediate/stabilize/restart/prevention stages.",
            "It does not infer incident parameters from public narratives or establish that any response action is correct or effective in the field.",
        ],
    }


def write_outputs(result: dict[str, Any]) -> None:
    OUT_JSON.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    lines = [
        "# HIAD runtime response handoff audit",
        "",
        "This audit executes one canonical fixture per mapped HIAD family and checks",
        "the actual monitor → response-selection → staged-guidance path.",
        "",
        f"- Executable family fixtures: **{result['runtime']['unique_family_recipes_run']}**",
        f"- Response handoffs passed: **{result['runtime']['response_handoff_pass_count']}/{result['runtime']['unique_family_recipes_run']}**",
        "",
        "| Family | Result | Selected response family | Guidance stages |",
        "| --- | --- | --- | --- |",
    ]
    for family, row in result["family_results"].items():
        ids = ", ".join(f"`{value}`" for value in row["selected_plan_ids"]) or "none"
        stages = "yes" if row["checks"]["staged_guidance_complete"] else "no"
        lines.append(f"| `{family}` | `{row['status']}` | {ids} | `{stages}` |")
    lines += ["", "## Claim boundary", "", *[f"- {item}" for item in result["claim_boundary"]], ""]
    OUT_MD.write_text("\n".join(lines), encoding="utf-8", newline="\n")


def main() -> None:
    result = build_audit()
    write_outputs(result)
    print(json.dumps(result["runtime"], ensure_ascii=False, indent=2))
    if not result["runtime"]["all_executable_handoffs_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
