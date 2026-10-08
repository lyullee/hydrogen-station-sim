"""Verify that bounded HyDelta flare evidence reaches the correct runtime paths."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any


def audit(root: Path) -> dict[str, Any]:
    root = root.resolve()
    sys.path.insert(0, str(root / "src"))
    from h2station.llm_grounding import (  # pylint: disable=import-outside-toplevel
        build_evidence_manifest,
        prompt_decision_evidence,
        prompt_evidence_header,
    )

    evidence_path = root / "research/hydelta_controlled_flare_evidence_2026_10_08.json"
    playbook_path = root / "src/h2station/data/emergency_playbooks.json"
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    playbooks = json.loads(playbook_path.read_text(encoding="utf-8"))
    plans = {item["id"]: item for item in playbooks.get("plans") or []}
    relevant_ids = ("relief_discharge", "vent_fault")
    relevant = {plan_id: plans.get(plan_id) or {} for plan_id in relevant_ids}

    frame = {"time_s": 1.0, "header_pressure_mpa": 45.0}
    idle_manifest = build_evidence_manifest(frame, {}, [], False)
    active_manifest = build_evidence_manifest(
        frame,
        {},
        [],
        False,
        active_conditions=[{
            "scenario": "안전밸브 개방·벤트 방출",
            "response_plan_id": "relief_discharge",
            "response_source_ids": ["HYDELTA_FLARE_2026"],
        }],
    )
    idle_prompt = prompt_decision_evidence(idle_manifest)
    active_prompt = prompt_decision_evidence(active_manifest)
    active_flare = (active_prompt.get("response_guidance") or {}).get(
        "controlled_flare"
    ) or {}
    header = prompt_evidence_header(active_manifest).get(
        "public_controlled_flare_evidence"
    ) or {}

    source = (playbooks.get("sources") or {}).get("HYDELTA_FLARE_2026") or {}
    action_text = " ".join(
        str(value)
        for plan in relevant.values()
        for stage in ("recognition", "immediate", "stabilize", "restart", "prevention")
        for value in plan.get(stage) or []
    )
    checks = {
        "evidence_status_verified": evidence.get("status")
        == "verified_report_level_controlled_flare_evidence",
        "source_doi_registered": source.get("url")
        == "https://doi.org/10.5281/zenodo.20817291",
        "source_license_registered": source.get("license") == "CC BY 4.0",
        "relevant_plans_link_source": all(
            "HYDELTA_FLARE_2026" in relevant[plan_id].get("sources", [])
            for plan_id in relevant_ids
        ),
        "ad_hoc_ignition_prohibited_in_playbook": "임의 점화하지 않는다" in action_text,
        "equipment_specific_nitrogen_boundary_stated": (
            "34 vol% N2" in action_text and "고유값" in action_text
        ),
        "idle_compact_prompt_omits_flare": "controlled_flare" not in (
            idle_prompt.get("response_guidance") or {}
        ),
        "active_compact_prompt_includes_flare": bool(active_flare),
        "active_prompt_keeps_engineered_only_boundary": active_flare.get(
            "engineered_approved_system_only"
        ) is True,
        "active_prompt_prohibits_ad_hoc_ignition": active_flare.get(
            "ad_hoc_vent_ignition_authorized"
        ) is False,
        "active_prompt_keeps_equipment_specific_value": active_flare.get(
            "tested_nitrogen_boundary_volpct"
        ) == 34.0,
        "detailed_header_keeps_no_release_validation_boundary": (
            (header.get("runtime_use") or {}).get("station_release_model_validation")
            is False
        ),
    }
    status = "PASS" if all(checks.values()) else "FAIL"
    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "source": {
            "doi": "10.5281/zenodo.20817291",
            "evidence": str(evidence_path.relative_to(root)).replace("\\", "/"),
            "playbook": str(playbook_path.relative_to(root)).replace("\\", "/"),
        },
        "checks": checks,
        "runtime_observation": {
            "relevant_plan_ids": list(relevant_ids),
            "idle_prompt_has_controlled_flare": not checks[
                "idle_compact_prompt_omits_flare"
            ],
            "active_prompt_controlled_flare": active_flare,
        },
        "claim_boundary": (
            "This audit verifies evidence routing and guardrails only. It does not "
            "validate a station release model, site safety distance, flare design or "
            "the effectiveness of a field emergency response."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(
            "research/hydelta_controlled_flare_runtime_grounding_2026_10_08.json"
        ),
    )
    args = parser.parse_args()
    result = audit(args.root)
    output = args.output if args.output.is_absolute() else args.root / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
