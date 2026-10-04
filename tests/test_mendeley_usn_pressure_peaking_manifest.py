import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT / "research/mendeley_usn_pressure_peaking_manifest_2026_10_05.json"


def test_mendeley_manifest_confirms_raw_component_archive_without_full_loop_claim():
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    assert result["status"] == "completed_public_manifest_recheck"
    assert result["source"]["doi"] == "10.17632/pmk59x4hvc.1"
    assert result["source"]["license"] == "CC BY 4.0"
    assert result["public_manifest"]["case_count_expected"] == 10
    assert result["public_manifest"]["case_count_with_pressure_and_mass_flow"] == 10
    assert result["public_manifest"]["all_case_identities_present"] is True
    assert result["eligibility"]["component_consequence_holdout_eligible"] is True
    assert result["eligibility"]["full_loop_external_holdout_eligible"] is False


def test_mendeley_manifest_preserves_setup_boundary():
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    eligibility = result["eligibility"]
    assert eligibility["vent_geometry_and_initial_conditions_in_dataset_manifest"] is False
    assert eligibility["requires_associated_publication_for_setup_mapping"] is True
    assert "not a gaseous H70 station-to-vehicle" in result["claim_boundary"]
