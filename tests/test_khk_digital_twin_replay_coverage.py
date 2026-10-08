from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "research/khk_digital_twin_replay_coverage_2026_10_08.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_khk_replay_is_independent_complete_and_claim_bounded():
    audit = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    source = audit["source"]
    runtime = audit["runtime"]
    aggregate = audit["aggregate"]

    assert audit["artifact_type"] == (
        "khk_public_accident_to_digital_twin_canonical_replay_audit"
    )
    assert audit["status"] == "completed_independent_public_accident_integration_audit"
    for key in ("inventory", "access_verification", "precedent_map", "playbook_catalog"):
        assert source[key]["sha256"] == _sha256(ROOT / source[key]["path"])
    assert all(
        _sha256(ROOT / path) == digest
        for path, digest in source["model_input_sha256"].items()
    )
    assert source["public_report_text_used"] is False
    assert source["report_narrative_used_for_physical_parameters"] is False
    assert source["raw_pdf_mirrored"] is False

    assert aggregate["public_report_count"] == 23
    assert aggregate["incident_code_count"] == 26
    assert aggregate["in_scope_report_count"] == 22
    assert aggregate["in_scope_incident_code_count"] == 25
    assert aggregate["integration_trace_pass_report_count"] == 22
    assert aggregate["integration_trace_pass_incident_code_count"] == 25
    assert aggregate["out_of_scope_report_count"] == 1
    assert aggregate["out_of_scope_incident_code_count"] == 1
    assert aggregate["representation_report_counts"] == {
        "direct_canonical_family_replay": 12,
        "proxy_partial_replay": 10,
        "out_of_scope_non_hydrogen_chemical": 1,
    }

    assert runtime["backend"] == "HyRAM+ 6.1 native"
    assert runtime["mapped_family_count"] == 8
    assert runtime["family_recipe_count"] == 8
    assert runtime["family_recipe_pass_count"] == 8
    assert runtime["all_family_recipes_passed"] is True
    assert runtime["missing_runtime_families"] == []
    assert runtime["missing_playbook_ids"] == []
    assert all(row["status"] == "passed" for row in audit["family_recipes"].values())

    koh = [case for case in audit["cases"] if case["equipment_class"] == "hydrogen_generation"]
    assert len(koh) == 1
    assert koh[0]["incident_codes"] == ["2024-349"]
    assert koh[0]["representation"] == "out_of_scope_non_hydrogen_chemical"
    assert koh[0]["integration_trace_pass"] is False
    assert koh[0]["excluded_from_executable_denominator"] is True
    assert all(
        case["integration_trace_pass"]
        for case in audit["cases"]
        if not case["excluded_from_executable_denominator"]
    )
    assert audit["claims"] == {
        "accident_reconstruction_claimed": False,
        "physics_validation_claimed": False,
        "response_effectiveness_claimed": False,
        "frequency_estimation_claimed": False,
        "safe_distance_claimed": False,
    }
