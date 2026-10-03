from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from audit_hiad_response_stage_contract import audit  # noqa: E402


def test_public_hiad_mappings_have_all_response_stages_and_quiet_idle_contract():
    result = audit()
    assert result["evidence_role"] == "metadata_only_response_contract"
    assert result["contract_pass"] is True
    aggregate = result["aggregate"]
    assert aggregate["case_count"] == 34
    assert aggregate["mapped_case_count"] == 34
    assert aggregate["missing_stage_case_count"] == 0
    assert aggregate["normal_quiet_contract_passed"] is True
    assert result["exception_ids"]["ignition_without_hydrogen_fire"] == []
    assert result["exception_ids"]["structural_without_structural_plan"] == []
    assert result["exception_ids"]["no_release_with_fire_plan"] == []


def test_stage_contract_output_is_reproducible_against_current_catalog_hash():
    result = audit()
    catalog = json.loads((ROOT / "src/h2station/data/emergency_playbooks.json").read_text(encoding="utf-8"))
    assert result["catalog"]["plan_count"] == len(catalog["plans"]) == 16
    assert set(result["catalog"]["required_stages"]) == {
        "recognition", "immediate", "stabilize", "restart", "prevention"
    }
