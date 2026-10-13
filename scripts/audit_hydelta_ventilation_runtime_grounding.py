"""Verify bounded HyDelta ventilation evidence routing and recovery guardrails."""

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

    evidence_path = (
        root / "research/hydelta_natural_ventilation_evidence_2026_10_13.json"
    )
    playbook_path = root / "src/h2station/data/emergency_playbooks.json"
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    playbooks = json.loads(playbook_path.read_text(encoding="utf-8"))
    plans = {item["id"]: item for item in playbooks.get("plans") or []}
    gas_release = plans.get("gas_release") or {}

    frame = {"time_s": 1.0, "header_pressure_mpa": 45.0}
    idle_manifest = build_evidence_manifest(frame, {}, [], False)
    active_manifest = build_evidence_manifest(
        frame,
        {},
        [],
        False,
        active_conditions=[{
            "scenario": "수소 누출·가스검지 상승",
            "response_plan_id": "gas_release",
            "response_source_ids": ["HYDELTA_VENTILATION_2023"],
        }],
    )
    idle_prompt = prompt_decision_evidence(idle_manifest)
    active_prompt = prompt_decision_evidence(active_manifest)
    active_guidance = (active_prompt.get("response_guidance") or {}).get(
        "natural_ventilation"
    ) or {}
    header = prompt_evidence_header(active_manifest)
    detailed = header.get("public_natural_ventilation_evidence") or {}
    source_links = header.get("public_source_links") or []

    source = (playbooks.get("sources") or {}).get(
        "HYDELTA_VENTILATION_2023"
    ) or {}
    action_text = " ".join(
        str(value)
        for stage in ("recognition", "immediate", "stabilize", "restart", "prevention")
        for value in gas_release.get(stage) or []
    )
    runtime_use = evidence.get("runtime_use") or {}
    identity = (evidence.get("source") or {}).get("publisher_file_identity") or {}
    checks = {
        "evidence_status_verified": evidence.get("status")
        == "verified_report_level_natural_ventilation_evidence",
        "publisher_file_identity_verified": identity.get("identity_match") is True,
        "all_report_claim_checks_pass": bool(evidence.get("claim_checks"))
        and all(value is True for value in evidence["claim_checks"].values()),
        "source_doi_registered": source.get("url")
        == "https://doi.org/10.5281/zenodo.8164602",
        "source_license_registered": source.get("license") == "CC BY 4.0",
        "gas_release_plan_links_source": "HYDELTA_VENTILATION_2023"
        in gas_release.get("sources", []),
        "ventilation_status_alone_rejected_in_playbook": (
            "환기가 작동한다는 표시만으로 안전을 선언하지 않는다" in action_text
        ),
        "independent_measurement_required_in_playbook": "독립 계측" in action_text,
        "idle_compact_prompt_omits_ventilation_guidance": "natural_ventilation"
        not in (idle_prompt.get("response_guidance") or {}),
        "active_compact_prompt_includes_ventilation_guidance": bool(active_guidance),
        "active_prompt_rejects_ventilation_only_clearance": active_guidance.get(
            "ventilation_as_single_safe_state_proof_authorized"
        ) is False,
        "active_prompt_requires_measured_clearance": active_guidance.get(
            "measured_gas_clearance_required"
        ) is True,
        "active_prompt_requires_measurement_before_opening": active_guidance.get(
            "measure_before_opening_recommended"
        ) is True,
        "detailed_header_keeps_no_dispersion_calibration_boundary": (
            (detailed.get("runtime_use") or {}).get("dispersion_proxy_calibration")
            is False
        ),
        "detailed_header_keeps_no_site_distance_boundary": (
            (detailed.get("runtime_use") or {}).get("site_safety_distance_validation")
            is False
        ),
        "public_source_link_exposed": any(
            item.get("id") == "HYDELTA_VENTILATION_2023"
            and item.get("url") == "https://doi.org/10.5281/zenodo.8164602"
            for item in source_links
        ),
        "runtime_use_is_response_only": (
            runtime_use.get("emergency_response_grounding") is True
            and runtime_use.get("station_release_model_validation") is False
            and runtime_use.get("alarm_setpoint_calibration") is False
        ),
    }
    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "PASS" if all(checks.values()) else "FAIL",
        "source": {
            "doi": "10.5281/zenodo.8164602",
            "evidence": str(evidence_path.relative_to(root)).replace("\\", "/"),
            "playbook": str(playbook_path.relative_to(root)).replace("\\", "/"),
        },
        "checks": checks,
        "runtime_observation": {
            "relevant_plan_ids": ["gas_release"],
            "idle_prompt_has_natural_ventilation_guidance": not checks[
                "idle_compact_prompt_omits_ventilation_guidance"
            ],
            "active_prompt_natural_ventilation": active_guidance,
        },
        "claim_boundary": (
            "This audit verifies report identity, playbook routing and recovery "
            "guardrails only. It does not validate H70 dispersion, detector placement, "
            "alarm thresholds, ESD effectiveness, release rate, site distance or field "
            "response effectiveness."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(
            "research/hydelta_natural_ventilation_runtime_grounding_2026_10_13.json"
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
