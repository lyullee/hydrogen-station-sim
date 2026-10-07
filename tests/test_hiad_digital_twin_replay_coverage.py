from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "research/hiad_digital_twin_replay_coverage_2026_10_08.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_hiad_replay_artifact_is_current_complete_and_bounded():
    audit = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    source = audit["source"]
    aggregate = audit["aggregate"]
    recipes = audit["family_recipes"]

    assert audit["artifact_type"] == "hiad_to_digital_twin_canonical_replay_coverage_audit"
    assert audit["status"] == "completed_family_level_integration_audit"
    assert source["public_response_text_used"] is False
    assert source["case_narrative_used_for_physical_parameters"] is False
    assert source["hiad_inventory_sha256"] == _sha256(ROOT / source["hiad_inventory"])
    assert source["playbook_catalog_sha256"] == _sha256(ROOT / source["playbook_catalog"])
    assert all(_sha256(ROOT / path) == digest for path, digest in source["model_input_sha256"].items())

    assert audit["runtime"]["backend"] == "HyRAM+ 6.1 native"
    assert audit["runtime"]["family_recipe_pass_count"] == 7
    assert audit["runtime"]["all_executable_recipes_passed"] is True
    assert aggregate["case_count"] == 34
    assert aggregate["integration_trace_pass_count"] == 34
    assert aggregate["representation_case_counts"] == {
        "direct_physical_replay": 29,
        "proxy_partial_replay": 4,
        "response_only_no_physical_model": 1,
        "unmapped": 0,
    }
    assert len(audit["cases"]) == 34
    assert len({case["event_id"] for case in audit["cases"]}) == 34
    assert all(case["integration_trace_pass"] for case in audit["cases"])
    assert all("title" not in case and "narrative" not in case for case in audit["cases"])

    for family in (
        "gas_release", "hydrogen_fire", "hose_connection", "overpressure",
        "precooling_fault", "fueling_fault", "compressor_thermal",
    ):
        assert recipes[family]["status"] == "passed"
        assert all(recipes[family]["checks"].values())
    assert recipes["hydrogen_fire"]["checks"]["flame_detection"] is True
    assert recipes["hydrogen_fire"]["checks"]["ignited_consequence"] is True
    assert recipes["gas_release"]["checks"]["native_consequence"] is True
    assert recipes["hose_connection"]["checks"]["native_consequence"] is True
    assert recipes["compressor_thermal"]["representation"] == "proxy_partial_replay"
    assert recipes["structural_damage"]["status"] == "not_run_no_physical_model"
    assert recipes["structural_damage"]["representation"] == "response_only_no_physical_model"
    assert len(audit["claim_boundary"]) >= 4
