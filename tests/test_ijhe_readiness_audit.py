from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from audit_ijhe_readiness import audit  # noqa: E402


def test_current_evidence_audit_passes_verified_components_and_blocks_completion():
    report = audit(ROOT)
    gates = {item["id"]: item for item in report["gates"]}

    assert gates["tank_external_validation"]["status"] == "PASS"
    assert gates["hyram_adapter_verification"]["status"] == "PASS"
    assert gates["elvhys_auxiliary_replay_integrity"]["status"] == "PASS"
    assert gates["elvhys_auxiliary_replay_integrity"]["observed"]["case_count"] == 3
    assert gates["elvhys_auxiliary_replay_integrity"]["observed"][
        "predictive_model_validation_permitted"
    ] is False
    assert gates["preoutcome_design_sensitivity"]["status"] == "PASS"
    assert gates["full_loop_external_validation"]["status"] == "FAIL"
    assert gates["nrel_h2fills_workbook_provenance_integrity"]["status"] == "PASS"
    assert gates["public_dispenser_endpoint_diagnostic"]["status"] == "PASS"
    assert gates["hiad_action_evidence_integrity"]["status"] == "PASS"
    assert gates["hiad_action_evidence_integrity"]["observed"]["case_count"] == 34
    assert gates["public_dispenser_endpoint_diagnostic"]["observed"]["stop_reason_counts"] == {"safety-temperature": 2}
    assert gates["accidental_release_ignition_public_evidence"]["status"] == "PASS"
    accidental = gates["accidental_release_ignition_public_evidence"]["observed"]
    assert accidental["zenodo_doi"] == "10.5281/zenodo.17913628"
    assert accidental["license"] == "CC BY 4.0"
    assert accidental["file_count"] == 3
    assert accidental["eligibility"]["full_loop_station_vehicle_holdout_eligible"] is False
    assert gates["khk_public_accident_report_inventory"]["status"] == "PASS"
    khk = gates["khk_public_accident_report_inventory"]["observed"]
    assert khk["coverage"]["pdf_report_count"] == 23
    assert khk["coverage"]["incident_code_count"] == 26
    assert khk["coverage"]["precaution_report_count"] == 8
    assert khk["rights_and_mirroring"]["raw_pdf_mirrored"] is False
    assert khk["eligibility"]["full_loop_station_vehicle_holdout_eligible"] is False
    assert gates["preslhy_blowdown_external_validation"]["status"] == "FAIL"
    assert gates["preslhy_blowdown_external_validation"]["observed"]["aggregate"][
        "joint_primary_pass_fraction"
    ] == 0.5
    assert gates["preslhy_partb_ambient_external_validation"]["status"] == "FAIL"
    partb = gates["preslhy_partb_ambient_external_validation"]["observed"]
    assert partb["eligibility"]["eligible_cases"] == 5
    assert partb["aggregate"]["joint_primary_pass_fraction"] == 0.6
    assert partb["aggregate"]["ambient_cryostat_part_b_claim_supported"] is False
    assert partb["protocol_hash_matches"] is True
    assert gates["preslhy_revised_holdout_validation"]["status"] == "FAIL"
    revised = gates["preslhy_revised_holdout_validation"]["observed"]
    assert revised["primary_cases"] == 3
    assert revised["aggregate"]["joint_primary_passes"] == 2
    assert revised["aggregate"]["minimum_requirements_met"] is False
    assert revised["aggregate"]["claim_supported"] is False
    assert revised["protocol_hash_matches"] is True
    assert gates["proust_independent_release_validation"]["status"] == "FAIL"
    proust = gates["proust_independent_release_validation"]["observed"]
    assert proust["aggregate"]["series"] == 3
    assert proust["aggregate"]["joint_primary_passes"] == 0
    assert proust["aggregate"]["minimum_requirements_met"] is True
    assert proust["aggregate"]["claim_supported"] is False
    assert proust["protocol_hash_matches"] is True
    assert proust["data_hash_matches"] is True
    assert gates["release_network_development_integrity"]["status"] == "PASS"
    assert gates["partial_station_profile_diagnostic_integrity"]["status"] == "PASS"
    partial = gates["partial_station_profile_diagnostic_integrity"]["observed"]
    assert partial["case_count"] == 8
    assert partial["screening_pass_count"] == 0
    assert partial["protocol"]["fresh_holdout"] is False
    assert gates["mc_source_schedule_diagnostic_integrity"]["status"] == "PASS"
    mc_partial = gates["mc_source_schedule_diagnostic_integrity"]["observed"]
    assert mc_partial["case_count"] == 8
    assert mc_partial["screening_pass_count"] == 1
    assert mc_partial["protocol"]["fresh_holdout"] is False
    release_development = gates["release_network_development_integrity"]["observed"]
    assert release_development["evidence_role"] == "consumed_development_only"
    assert release_development["eligible_as_confirmatory_validation"] is False
    assert release_development["interpretation"]["claim_supported"] is False
    assert gates["schefer_transient_release_validation"]["status"] == "FAIL"
    schefer = gates["schefer_transient_release_validation"]["observed"]
    assert schefer["result"]["points"] == 25
    assert schefer["result"]["nrmse_screen_pass"] is True
    assert schefer["result"]["median_ape_screen_pass"] is False
    assert schefer["result"]["half_peak_time_screen_pass"] is False
    assert schefer["protocol_hash_matches"] is True
    assert schefer["data_hash_matches"] is True
    assert gates["schefer_2007_pressure_decay_validation"]["status"] == "FAIL"
    schefer_2007 = gates["schefer_2007_pressure_decay_validation"]["observed"]
    assert schefer_2007["result"]["points"] == 222
    assert schefer_2007["result"]["nrmse_screen_pass"] is False
    assert schefer_2007["result"]["median_ape_screen_pass"] is False
    assert schefer_2007["result"]["half_pressure_time_screen_pass"] is True
    assert schefer_2007["protocol_hash_matches"] is True
    assert schefer_2007["data_hash_matches"] is True
    assert gates["grune_2014_pressure_decay_validation"]["status"] == "PENDING"
    grune = gates["grune_2014_pressure_decay_validation"]["observed"]
    assert grune["eligibility"]["minimum_requirements_met"] is False
    assert grune["eligibility"]["measured_half_pressure_time_observed"] is False
    assert grune["result"]["points"] == 51
    assert grune["hashes_match"] is True
    assert gates["ekoto_transient_release_validation"]["status"] == "PASS"
    ekoto = gates["ekoto_transient_release_validation"]["observed"]
    assert ekoto["result"]["points"] == 39
    assert ekoto["result"]["nrmse_screen_pass"] is True
    assert ekoto["result"]["median_ape_screen_pass"] is True
    assert ekoto["result"]["half_peak_time_screen_pass"] is True
    assert ekoto["protocol_hash_matches"] is True
    assert ekoto["data_hash_matches"] is True
    external = gates["full_loop_external_validation"]["observed"]
    assert external["protocol_integrity"] is True
    assert external["aggregate"]["case_count"] == 8
    assert external["aggregate"]["screening_pass_count"] == 0
    assert external["aggregate"]["screening_pass_fraction"] == 0.0
    assert (
        external["new_external_data_search"]["status"]
        == "NO_ELIGIBLE_PUBLIC_RAW_SET_IDENTIFIED"
    )
    assert gates["institutional_ethics_determination"]["status"] == "PENDING"
    assert gates["independent_expert_review_complete"]["status"] == "PENDING"
    assert report["bounded_ijhe_submission_ready"] is False
    assert report["full_user_objective_ready"] is False
    assert report["goal_completion_permitted"] is False


def test_full_objective_gate_is_stricter_than_bounded_submission_gate():
    report = audit(ROOT)
    bounded = set(report["blocking_bounded_submission_gates"])
    full = set(report["blocking_full_objective_gates"])
    assert bounded < full
    assert "full_loop_external_validation" in full - bounded
    assert "saga_effectiveness_and_safety_supported" in full - bounded
    geometry = next(
        gate for gate in report["gates"]
        if gate["id"] == "station_consequence_geometry_validation"
    )
    assert geometry["status"] == "PASS"
