import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT / "research/hydelta_indoor_spatial_holdout_eligibility_2026_10_08.json"


def _result():
    return json.loads(RESULT.read_text(encoding="utf-8"))


def test_hydelta_actual_hydrogen_report_is_audited_without_rescuing_figures():
    record = _result()
    assert record["status"] == "INELIGIBLE_NO_MODEL_EVALUATION"
    assert record["source"]["doi"] == "10.5281/zenodo.8154318"
    assert record["source"]["license"] == "CC BY 4.0"
    assert record["source"]["publisher_file_identity"]["identity_match"] is True
    assert record["protocol"]["pre_access_status"] == "FROZEN_BEFORE_REPORT_FILE_ACCESS"
    assert record["protocol"]["formula_change_after_access"] is False
    assert record["protocol"]["figure_digitisation_performed"] is False


def test_hydelta_ineligibility_keeps_runtime_and_validation_claim_closed():
    record = _result()
    decision = record["decision"]
    assert decision["eligible_for_primary_spatial_holdout"] is False
    assert decision["model_evaluation_executed"] is False
    assert decision["independent_validation_pass"] is False
    assert decision["runtime_candidate_enabled"] is False
    assert set(decision["failed_required_fields"]) == {
        "source_coordinates",
        "sensor_coordinates_in_same_frame",
        "release_orientation_class",
        "per_sensor_numeric_response",
    }


def test_hydelta_retains_bounded_actual_hydrogen_context():
    record = _result()
    evidence = record["usable_evidence"]
    assert evidence["actual_hydrogen_experiment_count_inventory"] == 32
    assert evidence["sensor_count"] == 50
    assert evidence["release_rates_normal_dm3_h"] == [50, 100, 300, 1000]
    assert evidence["configuration_count"] == 8
    assert "does not independently validate" in record["claim_boundary"]
