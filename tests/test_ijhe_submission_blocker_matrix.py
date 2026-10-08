import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_current_blocker_matrix_tracks_the_readiness_audit():
    audit = json.loads((ROOT / "manuscript/ijhe_readiness_audit.json").read_text(encoding="utf-8"))
    matrix = json.loads(
        (ROOT / "research/ijhe_submission_blocker_matrix_2026_10_05.json")
        .read_text(encoding="utf-8")
    )
    assert matrix["gate_counts"] == audit["gate_counts"]
    assert matrix["reproducibility"]["public_full_loop_search_candidate_count"] == 17
    assert matrix["reproducibility"]["public_operational_benchmark_candidate_count"] == 18
    assert matrix["decision"]["goal_completion_permitted"] is False
    assert matrix["decision"]["full_user_objective_ready"] is False
    h2safe = matrix["evidence_snapshot"]["full_scale_indoor_surrogate_measurements"]
    assert h2safe["gate"] == "PASS"
    assert "helium-surrogate" in h2safe["claim_boundary"]
    reference_detector = matrix["evidence_snapshot"][
        "physical_hydrogen_reference_leak_detector_response"
    ]
    assert reference_detector["gate"] == "PASS"
    assert reference_detector["observation_count"] == 45
    assert len(reference_detector["series"]) == 3
    assert all(item["joint_pass"] for item in reference_detector["series"])
    assert reference_detector["runtime_application"] is False
    assert len(
        matrix["reproducibility"]["reference_leak_detector_result_sha256"]
    ) == 64
    spatial = matrix["evidence_snapshot"][
        "actual_hydrogen_spatial_stratification"
    ]
    assert spatial["gate"] == "PASS"
    assert spatial["experiment_count"] == 22
    assert spatial["sensor_case_observation_count"] == 638
    assert spatial["top_alarm_coverage_fraction"] == 1.0
    assert spatial["top_trip_coverage_fraction"] == 1.0
    assert spatial["near_source_bottom_alarm_latency_s"] < 11.0
    assert spatial["runtime_application"] is False
    assert spatial["h2safe_gate_changed"] is False
    assert len(
        matrix["reproducibility"]["usn_spatial_stratification_sha256"]
    ) == 64
    assert len(matrix["reproducibility"]["h2safe_intake_sha256"]) == 64
    assert len(matrix["reproducibility"]["hydelta_spatial_eligibility_sha256"]) == 64
    transfer = matrix["evidence_snapshot"]["h2safe_spatial_detector_transfer"]
    actual_hydrogen = transfer["actual_hydrogen_holdout_candidate"]
    assert actual_hydrogen["status"] == "INELIGIBLE_NO_MODEL_EVALUATION"
    assert actual_hydrogen["eligible"] is False
    assert actual_hydrogen["model_evaluation_executed"] is False
    assert actual_hydrogen["runtime_candidate_enabled"] is False
    sandia = transfer["actual_hydrogen_external_diagnostic"]
    assert sandia["status"] == "EXTERNAL_POST_ACCESS_DIAGNOSTIC_NOT_VALIDATION"
    assert sandia["sensor_count"] == 6
    assert sandia["candidate_spearman_rho"] > 0.94
    assert sandia["top3_recall"] == 1.0
    assert sandia["independent_validation_pass"] is False
    assert sandia["runtime_candidate_enabled"] is False
    assert len(matrix["reproducibility"]["sandia_spatial_diagnostic_sha256"]) == 64
    hytunnel = transfer["actual_hydrogen_independent_holdout"]
    assert hytunnel["execution_integrity_gate"] == "PASS"
    assert hytunnel["experiment_count"] == 18
    assert hytunnel["median_spearman"] > 0.56
    assert hytunnel["spearman_at_least_0_4_fraction"] > 0.83
    assert 0.57 < hytunnel["mean_top5_recall"] < 0.6
    assert hytunnel["nearest_in_response_quartile_fraction"] > 0.94
    assert hytunnel["screens"]["mean_top5_recall_at_least_0_6"] is False
    assert hytunnel["joint_screen_pass"] is False
    assert hytunnel["runtime_candidate_enabled"] is False
    assert len(matrix["reproducibility"]["hytunnel_spatial_protocol_sha256"]) == 64
    assert len(matrix["reproducibility"]["hytunnel_spatial_amendment_sha256"]) == 64
    assert len(matrix["reproducibility"]["hytunnel_spatial_result_sha256"]) == 64
    ids = {item["id"] for item in matrix["blocking_matrix"]}
    assert {
        "tank_thermal_transfer_validation",
        "full_loop_external_validation",
        "saga_human_effectiveness",
        "submission_declarations",
    } <= ids
    typeiii = matrix["evidence_snapshot"]["typeiii_prospective_fill"]
    assert typeiii["gate"] == "FAIL"
    assert typeiii["diagnostic_gate"] == "PASS"
