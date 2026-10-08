from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "research/hiad_runtime_response_handoff_2026_10_09.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_hiad_runtime_response_handoff_is_complete_and_integrity_checked():
    audit = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    source = audit["source"]
    runtime = audit["runtime"]
    results = audit["family_results"]

    assert audit["artifact_type"] == "hiad_runtime_response_handoff_audit"
    assert audit["status"] == "completed_canonical_family_handoff_audit"
    assert _sha256(ROOT / source["replay_coverage_artifact"]) == source["replay_coverage_artifact_sha256"]
    assert _sha256(ROOT / source["response_module"]) == source["response_module_sha256"]
    assert _sha256(ROOT / source["playbook_catalog"]) == source["playbook_catalog_sha256"]
    assert runtime["unique_family_recipes_run"] == 9
    assert runtime["response_handoff_pass_count"] == 9
    assert runtime["all_executable_handoffs_passed"] is True

    expected = {
        "gas_release": "gas_release",
        "hydrogen_fire": "hydrogen_fire",
        "hose_connection": "gas_release",
        "overpressure": "overpressure",
        "precooling_fault": "precooling_fault",
        "fueling_fault": "low_supply_or_blockage",
        "compressor_thermal": "external_fire",
        "external_fire": "external_fire",
        "isolation_failure": "fueling_fault",
    }
    assert set(results) == set(expected)
    for family, plan_id in expected.items():
        row = results[family]
        assert row["status"] == "passed"
        assert plan_id in row["selected_plan_ids"]
        assert plan_id in row["guidance_plan_ids"]
        assert all(value for key, value in row["checks"].items()
                   if key != "consequence_evidence_present")
    # This assertion guards the regression that motivated the audit: an
    # ignited release must reach the dedicated hydrogen-fire plan.
    assert results["hydrogen_fire"]["selected_plan_ids"][0] == "hydrogen_fire"
    assert all("narrative" not in row for row in results.values())
