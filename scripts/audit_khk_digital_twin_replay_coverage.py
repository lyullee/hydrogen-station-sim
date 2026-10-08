"""Trace public KHK accident metadata through canonical digital-twin recipes.

The KHK reports provide independent accident precedents, but not synchronized
boundary traces suitable for accident reconstruction.  This audit therefore
checks whether each in-scope report family can traverse an explicitly declared
canonical runtime recipe.  It keeps non-hydrogen chemical releases and phase or
equipment mismatches visible instead of treating them as validated replays.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from audit_hiad_digital_twin_replay_coverage import (  # noqa: E402
    MODEL_INPUTS,
    _recipe_catalog,
    _run_recipe,
    _sha256,
)


INVENTORY = ROOT / "research/khk_hydrogen_station_public_reports_inventory_2026_10_04.json"
ACCESS = ROOT / "research/khk_public_reports_access_verification_2026_10_04.json"
PRECEDENT_MAP = ROOT / "research/khk_scenario_precedent_map_2026_10_04.json"
PLAYBOOKS = ROOT / "src/h2station/data/emergency_playbooks.json"
OUT_JSON = ROOT / "research/khk_digital_twin_replay_coverage_2026_10_08.json"
OUT_MD = ROOT / "research/KHK_DIGITAL_TWIN_REPLAY_COVERAGE_2026_10_08.md"

OUT_OF_SCOPE_CLASSES = {
    "hydrogen_generation": (
        "The recorded release is KOH electrolyte, not gaseous hydrogen; the "
        "current H70 process model has no caustic-liquid transport model."
    ),
}

# These reports remain useful independent precedents, but their phase,
# equipment, or event sequence is not represented one-for-one by the canonical
# gaseous-H70 station fixture.
PROXY_CLASSES = {
    "dehumidifier_ignition": "Hydrogen-production dehumidifier geometry is outside the station process model.",
    "explosion": "The canonical fire and pressure fixtures do not reconstruct the explosion source term.",
    "filling_equipment_explosion": "The combined filling-equipment explosion sequence is represented by separate fueling and pressure fixtures.",
    "vehicle_fire": "The source report concerns liquid hydrogen and an engine-room fire; the model is gaseous H70.",
    "leak_static_ignition": "Hydrogen-production equipment and electrostatic ignition physics are outside the modeled station equipment.",
    "compressor_leak": "The compressor has no independent dynamic gas inventory; storage release and compressor heat are bounded proxies.",
    "isolation_valve_leak": "The failed-open PCV fixture does not reproduce valve-seat leakage or actuator feedback.",
    "dispenser_isolation_valve_leak": "The failed-open PCV fixture does not reproduce valve-seat leakage or actuator feedback.",
    "accumulator_fire": "The canonical bank heat-and-release fixtures do not reconstruct cleaning work or ignition history.",
    "station_explosion": "The canonical fire and pressure fixtures do not reconstruct the demonstration-equipment explosion.",
}


def _hash_record(path: Path) -> dict[str, str]:
    return {
        "path": str(path.relative_to(ROOT)).replace("\\", "/"),
        "sha256": _sha256(path),
    }


def _representation(
    equipment_class: str,
    plan_ids: list[str],
    catalog: dict[str, dict[str, Any]],
) -> tuple[str, str]:
    if equipment_class in OUT_OF_SCOPE_CLASSES:
        return "out_of_scope_non_hydrogen_chemical", OUT_OF_SCOPE_CLASSES[equipment_class]
    if equipment_class in PROXY_CLASSES:
        return "proxy_partial_replay", PROXY_CLASSES[equipment_class]
    if any(catalog[plan]["representation"] == "proxy_partial_replay" for plan in plan_ids):
        return "proxy_partial_replay", "At least one mapped family uses a bounded proxy fixture."
    return (
        "direct_canonical_family_replay",
        "The equipment family is represented directly, while source-report geometry and timing remain unused.",
    )


def build_audit() -> dict[str, Any]:
    inventory = json.loads(INVENTORY.read_text(encoding="utf-8"))
    access = json.loads(ACCESS.read_text(encoding="utf-8"))
    precedent = json.loads(PRECEDENT_MAP.read_text(encoding="utf-8"))
    playbooks = json.loads(PLAYBOOKS.read_text(encoding="utf-8"))
    valid_plan_ids = {str(row["id"]) for row in playbooks.get("plans", [])}
    catalog = _recipe_catalog()

    mapped_families = sorted({
        str(plan)
        for case in precedent.get("cases", [])
        if str(case.get("equipment_class")) not in OUT_OF_SCOPE_CLASSES
        for plan in case.get("playbook_ids", [])
    })
    missing_families = sorted(set(mapped_families) - set(catalog))
    missing_playbooks = sorted(set(mapped_families) - valid_plan_ids)
    recipe_results = {
        family: _run_recipe(family, catalog[family])
        for family in mapped_families
        if family in catalog and catalog[family].get("event") is not None
    }

    cases: list[dict[str, Any]] = []
    for case in precedent.get("cases", []):
        equipment_class = str(case.get("equipment_class"))
        plan_ids = [str(plan) for plan in case.get("playbook_ids", [])]
        representation, boundary = _representation(equipment_class, plan_ids, catalog)
        out_of_scope = representation == "out_of_scope_non_hydrogen_chemical"
        executed = [] if out_of_scope else [plan for plan in plan_ids if plan in recipe_results]
        failed = [plan for plan in executed if recipe_results[plan]["status"] != "passed"]
        integration_pass = (not out_of_scope) and bool(executed) and not failed
        cases.append({
            "incident_codes": [str(code) for code in case.get("incident_codes", [])],
            "title": str(case.get("title") or ""),
            "equipment_class": equipment_class,
            "source_url": str(case.get("url") or ""),
            "mapped_playbook_ids": plan_ids,
            "representation": representation,
            "representation_boundary": boundary,
            "executed_recipe_ids": executed,
            "failed_recipe_ids": failed,
            "integration_trace_pass": integration_pass,
            "excluded_from_executable_denominator": out_of_scope,
        })

    in_scope = [case for case in cases if not case["excluded_from_executable_denominator"]]
    out_of_scope = [case for case in cases if case["excluded_from_executable_denominator"]]
    all_codes = [code for case in cases for code in case["incident_codes"]]
    covered_codes = [
        code for case in in_scope if case["integration_trace_pass"]
        for code in case["incident_codes"]
    ]
    excluded_codes = [code for case in out_of_scope for code in case["incident_codes"]]
    representation_counts = {
        label: sum(case["representation"] == label for case in cases)
        for label in (
            "direct_canonical_family_replay",
            "proxy_partial_replay",
            "out_of_scope_non_hydrogen_chemical",
        )
    }
    passed_recipes = sum(row["status"] == "passed" for row in recipe_results.values())

    return {
        "schema_version": 1,
        "artifact_type": "khk_public_accident_to_digital_twin_canonical_replay_audit",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "completed_independent_public_accident_integration_audit",
        "evidence_role": "independent_retrospective_metadata_to_canonical_runtime_traceability_only",
        "source": {
            "inventory": _hash_record(INVENTORY),
            "access_verification": _hash_record(ACCESS),
            "precedent_map": _hash_record(PRECEDENT_MAP),
            "playbook_catalog": _hash_record(PLAYBOOKS),
            "model_input_sha256": {
                str(path.relative_to(ROOT)).replace("\\", "/"): _sha256(path)
                for path in MODEL_INPUTS
            },
            "public_report_text_used": False,
            "report_narrative_used_for_physical_parameters": False,
            "raw_pdf_mirrored": False,
        },
        "runtime": {
            "backend": "HyRAM+ 6.1 native",
            "virtual_detector_mode": True,
            "mapped_family_count": len(mapped_families),
            "family_recipe_count": len(recipe_results),
            "family_recipe_pass_count": passed_recipes,
            "all_family_recipes_passed": passed_recipes == len(recipe_results),
            "missing_runtime_families": missing_families,
            "missing_playbook_ids": missing_playbooks,
        },
        "aggregate": {
            "public_report_count": len(cases),
            "incident_code_count": len(all_codes),
            "in_scope_report_count": len(in_scope),
            "in_scope_incident_code_count": len(all_codes) - len(excluded_codes),
            "integration_trace_pass_report_count": sum(
                case["integration_trace_pass"] for case in in_scope
            ),
            "integration_trace_pass_incident_code_count": len(covered_codes),
            "out_of_scope_report_count": len(out_of_scope),
            "out_of_scope_incident_code_count": len(excluded_codes),
            "representation_report_counts": representation_counts,
        },
        "family_recipes": recipe_results,
        "cases": cases,
        "claims": {
            "accident_reconstruction_claimed": False,
            "physics_validation_claimed": False,
            "response_effectiveness_claimed": False,
            "frequency_estimation_claimed": False,
            "safe_distance_claimed": False,
        },
        "claim_boundary": [
            "KHK metadata selects canonical response families; report text does not set pressure, temperature, opening size, enclosure geometry, heat flux or event timing.",
            "A passed trace means the mapped family can traverse process physics, virtual detection, safety logic and native consequence calculation where applicable.",
            "It does not reconstruct a KHK accident, validate physics or frequency, establish safe distance, or show that a response is correct or effective.",
            "The KOH electrolyte case is explicitly outside the gaseous-hydrogen model; liquid-hydrogen, production-equipment, explosion and valve-seat mechanisms remain bounded proxies.",
        ],
        "source_consistency": {
            "inventory_report_count": len(inventory.get("accident_reports", [])),
            "access_verified_report_count": int(access.get("verified_report_count", 0)),
            "precedent_mapped_report_count": int(
                (precedent.get("mapping") or {}).get("mapped_report_count", 0)
            ),
        },
    }


def write_outputs(result: dict[str, Any]) -> None:
    OUT_JSON.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8", newline="\n",
    )
    aggregate = result["aggregate"]
    counts = aggregate["representation_report_counts"]
    lines = [
        "# KHK public accidents to digital-twin canonical replay coverage",
        "",
        "This independent integration audit traces public KHK accident metadata",
        "through declared digital-twin fault recipes. It is not accident reconstruction",
        "or evidence that the simulated response is effective.",
        "",
        f"- Public reports / incident codes: **{aggregate['public_report_count']} / {aggregate['incident_code_count']}**",
        f"- In-scope reports / incident codes traced: **{aggregate['integration_trace_pass_report_count']} / {aggregate['integration_trace_pass_incident_code_count']}**",
        f"- Direct canonical family traces: **{counts['direct_canonical_family_replay']}** reports",
        f"- Bounded proxy/partial traces: **{counts['proxy_partial_replay']}** reports",
        f"- Explicitly out of scope: **{counts['out_of_scope_non_hydrogen_chemical']}** report",
        f"- Family recipes passed: **{result['runtime']['family_recipe_pass_count']}/{result['runtime']['family_recipe_count']}**",
        "",
        "## Report-level trace",
        "",
        "| Incident code(s) | Equipment class | Representation | Runtime result |",
        "| --- | --- | --- | --- |",
    ]
    for case in result["cases"]:
        outcome = (
            "excluded: non-H2 chemical"
            if case["excluded_from_executable_denominator"]
            else ("passed" if case["integration_trace_pass"] else "failed")
        )
        lines.append(
            f"| {', '.join(case['incident_codes'])} | `{case['equipment_class']}` | "
            f"`{case['representation']}` | {outcome} |"
        )
    lines.extend([
        "",
        "## Claim boundary",
        "",
        *[f"- {item}" for item in result["claim_boundary"]],
        "",
    ])
    OUT_MD.write_text("\n".join(lines), encoding="utf-8", newline="\n")


def main() -> int:
    result = build_audit()
    write_outputs(result)
    print(json.dumps({
        "status": result["status"],
        "aggregate": result["aggregate"],
        "runtime": result["runtime"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
