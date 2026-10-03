"""Audit the response-stage contract for public HIAD metadata mappings.

This is a deterministic interface/traceability check.  It verifies that every
public HIAD metadata row mapped by the existing candidate-family audit points
to registered playbooks with all five operator-facing stages.  It deliberately
does not read HIAD emergency-action text and does not claim that the advice is
correct, safe, effective, or complete for a real incident.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "research/hiad_hrs_public_evidence.json"
COVERAGE = ROOT / "research/hiad_playbook_coverage.json"
PLAYBOOKS = ROOT / "src/h2station/data/emergency_playbooks.json"
OUT_JSON = ROOT / "research/hiad_response_stage_contract.json"
OUT_MD = ROOT / "research/HIAD_RESPONSE_STAGE_CONTRACT.md"
STAGES = ("recognition", "immediate", "stabilize", "restart", "prevention")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _quiet_contract() -> dict[str, object]:
    """Check that an idle periodic frame does not manufacture an emergency plan."""
    src = str(ROOT / "src")
    if src not in sys.path:
        sys.path.insert(0, src)
    from h2station.hazop.database import load_catalog  # pylint: disable=import-outside-toplevel
    from h2station.hazop.response import (  # pylint: disable=import-outside-toplevel
        response_selection,
        structured_guidance,
    )

    frame = {"hazop": {"active": [], "releases": []}, "active_faults": []}
    selected = response_selection(frame, load_catalog(), trigger="periodic")
    guidance = structured_guidance(selected, actual_alert=False)
    return {
        "periodic_selection_empty": selected == [],
        "structured_guidance_none": guidance is None,
        "passed": selected == [] and guidance is None,
    }


def audit() -> dict[str, object]:
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    coverage = json.loads(COVERAGE.read_text(encoding="utf-8"))
    catalog = json.loads(PLAYBOOKS.read_text(encoding="utf-8"))
    plans = {str(plan["id"]): plan for plan in catalog.get("plans", [])}
    coverage_cases = {str(row["event_id"]): row for row in coverage.get("cases", [])}
    source_hash_matches = (
        coverage.get("source", {}).get("inventory_sha256") == _sha256(EVIDENCE)
    )
    catalog_hash_matches = (
        coverage.get("playbook_catalog", {}).get("catalog_sha256") == _sha256(PLAYBOOKS)
    )

    missing_stage_entries: list[dict[str, object]] = []
    invalid_plan_ids: list[dict[str, object]] = []
    case_rows: list[dict[str, object]] = []
    for case in evidence.get("cases", []):
        event_id = str(case["event_id"])
        row = coverage_cases.get(event_id, {})
        plan_ids = [str(item) for item in row.get("candidate_plan_ids", [])]
        invalid = [plan_id for plan_id in plan_ids if plan_id not in plans]
        if invalid:
            invalid_plan_ids.append({"event_id": event_id, "plan_ids": invalid})
        case_missing: list[dict[str, object]] = []
        for plan_id in plan_ids:
            plan = plans.get(plan_id)
            if plan is None:
                continue
            for stage in STAGES:
                value = plan.get(stage)
                if not isinstance(value, list) or not value or not all(str(item).strip() for item in value):
                    case_missing.append({"plan_id": plan_id, "stage": stage})
        if case_missing:
            missing_stage_entries.append({"event_id": event_id, "missing": case_missing})

        effect = str(case.get("physical_effect", "")).lower()
        title = str(case.get("title", "")).lower()
        consequence = str(case.get("consequence_nature", "")).lower()
        ignition_expected = (
            "release and ignition" in effect
            or consequence in {"fire", "explosion", "explosion followed by a fire"}
            or title.startswith("fire ")
            or title.startswith("explosion ")
        )
        structural_expected = any(
            token in " ".join((title, effect, str(case.get("sub_application", "")))).lower()
            for token in ("damage", "collision", "structural", "canopy")
        )
        case_rows.append({
            "event_id": event_id,
            "candidate_plan_ids": plan_ids,
            "stage_contract": "pass" if not case_missing and not invalid else "fail",
            "ignition_metadata_requires_hydrogen_fire": ignition_expected,
            "hydrogen_fire_present": "hydrogen_fire" in plan_ids,
            "structural_damage_metadata_requires_structural_plan": structural_expected,
            "structural_damage_present": "structural_damage" in plan_ids,
            "missing_stages": case_missing,
        })

    ignition_rows = [row for row in case_rows if row["ignition_metadata_requires_hydrogen_fire"]]
    structural_rows = [row for row in case_rows if row["structural_damage_metadata_requires_structural_plan"]]
    ignition_without_fire = [row["event_id"] for row in ignition_rows if not row["hydrogen_fire_present"]]
    structural_without_plan = [row["event_id"] for row in structural_rows if not row["structural_damage_present"]]
    no_release_with_fire = [
        str(case["event_id"])
        for case in evidence.get("cases", [])
        if "no hydrogen release" in str(case.get("physical_effect", "")).lower()
        and "hydrogen_fire" in coverage_cases.get(str(case["event_id"]), {}).get("candidate_plan_ids", [])
    ]
    quiet = _quiet_contract()
    aggregate = {
        "case_count": len(case_rows),
        "mapped_case_count": sum(bool(row["candidate_plan_ids"]) for row in case_rows),
        "plan_reference_count": sum(len(row["candidate_plan_ids"]) for row in case_rows),
        "missing_stage_case_count": len(missing_stage_entries),
        "invalid_plan_reference_count": len(invalid_plan_ids),
        "ignition_case_count": len(ignition_rows),
        "ignition_without_hydrogen_fire_count": len(ignition_without_fire),
        "structural_case_count": len(structural_rows),
        "structural_without_structural_plan_count": len(structural_without_plan),
        "no_release_with_fire_plan_count": len(no_release_with_fire),
        "normal_quiet_contract_passed": bool(quiet["passed"]),
        "coverage_source_hash_matches": source_hash_matches,
        "coverage_catalog_hash_matches": catalog_hash_matches,
    }
    contract_pass = bool(
        aggregate["case_count"] == 34
        and aggregate["mapped_case_count"] == 34
        and aggregate["missing_stage_case_count"] == 0
        and aggregate["invalid_plan_reference_count"] == 0
        and aggregate["ignition_without_hydrogen_fire_count"] == 0
        and aggregate["structural_without_structural_plan_count"] == 0
        and aggregate["no_release_with_fire_plan_count"] == 0
        and aggregate["normal_quiet_contract_passed"]
        and aggregate["coverage_source_hash_matches"]
        and aggregate["coverage_catalog_hash_matches"]
    )
    result: dict[str, object] = {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "completed_metadata_only_response_stage_contract",
        "evidence_role": "metadata_only_response_contract",
        "source": {
            "inventory": "research/hiad_hrs_public_evidence.json",
            "inventory_sha256": _sha256(EVIDENCE),
            "coverage": "research/hiad_playbook_coverage.json",
            "coverage_sha256": _sha256(COVERAGE),
            "public_source": evidence["source"]["url"],
        },
        "catalog": {
            "path": "src/h2station/data/emergency_playbooks.json",
            "catalog_sha256": _sha256(PLAYBOOKS),
            "plan_count": len(plans),
            "required_stages": list(STAGES),
        },
        "aggregate": aggregate,
        "contract_pass": contract_pass,
        "normal_quiet_contract": quiet,
        "exception_ids": {
            "missing_stage_cases": [row["event_id"] for row in missing_stage_entries],
            "invalid_plan_references": invalid_plan_ids,
            "ignition_without_hydrogen_fire": ignition_without_fire,
            "structural_without_structural_plan": structural_without_plan,
            "no_release_with_fire_plan": no_release_with_fire,
        },
        "cases": case_rows,
        "limitations": [
            "The audit uses public HIAD metadata and the local catalogue; HIAD emergency-action and lesson text are excluded.",
            "A complete stage contract verifies interface coverage only; it does not establish that any step is correct, safe or effective.",
            "No accident probability, consequence-distance, physics, human-factors or operator-performance claim is made.",
            "Independent coordinator review, blinded holdout scoring and qualified expert rating remain required.",
        ],
    }
    return result


def write_outputs(result: dict[str, object]) -> None:
    OUT_JSON.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    aggregate = result["aggregate"]
    exceptions = result["exception_ids"]
    lines = [
        "# HIAD response-stage contract audit",
        "",
        "This deterministic audit checks the operator-facing response contract for",
        "the public HIAD metadata mappings. It does not read HIAD emergency-action",
        "or lesson text and does not establish correctness, safety, effectiveness,",
        "or operator benefit.",
        "",
        f"- Contract result: **{'PASS' if result['contract_pass'] else 'FAIL'}**",
        f"- Cases mapped: **{aggregate['mapped_case_count']}/{aggregate['case_count']}**",
        f"- Required stages: **{', '.join(result['catalog']['required_stages'])}**",
        f"- Cases with missing stages: **{aggregate['missing_stage_case_count']}**",
        f"- Normal periodic quiet contract: **{'PASS' if aggregate['normal_quiet_contract_passed'] else 'FAIL'}**",
        f"- Coverage/source hashes: **{'PASS' if aggregate['coverage_source_hash_matches'] and aggregate['coverage_catalog_hash_matches'] else 'FAIL'}**",
        "",
        "## Contract checks",
        "",
        "Every mapped family must expose recognition, immediate action, stabilization,",
        "restart prerequisites and prevention/safety-management steps. Metadata that",
        "explicitly describes ignition must include the hydrogen-fire family; structural",
        "damage metadata must include the structural-damage family. A no-release row",
        "must not invent a fire plan.",
        "",
        f"- Ignition rows without a fire family: `{exceptions['ignition_without_hydrogen_fire']}`",
        f"- Structural rows without a structural family: `{exceptions['structural_without_structural_plan']}`",
        f"- No-release rows with a fire family: `{exceptions['no_release_with_fire_plan']}`",
        "",
        "## Claim boundary",
        "",
        "A passing result means the interface can carry staged, source-linked guidance",
        "for this metadata inventory and stays quiet on an idle periodic frame. It is",
        "not evidence that the stages are complete for a real site, that the physics",
        "or distances are valid, or that an operator would perform better.",
        "",
        f"Public source: `{result['source']['public_source']}`",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def main() -> None:
    result = audit()
    write_outputs(result)
    print(json.dumps(result["aggregate"], ensure_ascii=False, indent=2))
    if not result["contract_pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
