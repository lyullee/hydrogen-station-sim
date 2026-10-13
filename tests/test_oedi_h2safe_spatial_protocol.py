from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "research/oedi_h2safe_spatial_holdout_protocol_2026_10_14.json"
RESULT = ROOT / "research/oedi_h2safe_spatial_holdout_eligibility_2026_10_14.json"
MODEL = ROOT / "src/h2station/prospective_spatial_rank.py"
PARENT = ROOT / "research/prospective_spatial_rank_protocol_2026_10_13.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_oedi_protocol_is_preaccess_and_hash_locks_existing_candidate() -> None:
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    source = protocol["source"]
    candidate = protocol["locked_candidate"]

    assert source["detailed_landing_page_opened"] is False
    assert source["file_inventory_opened"] is False
    assert source["numerical_time_series_opened"] is False
    assert source["sensor_or_source_coordinate_values_opened"] is False
    assert source["outcome_plot_or_metric_opened"] is False
    assert candidate["implementation_sha256"] == _sha256(MODEL)
    assert candidate["parent_protocol_sha256"] == _sha256(PARENT)
    assert candidate["candidate_id"] == "pooled_spatial_rank_v1"


def test_oedi_protocol_retains_all_or_nothing_independent_holdout_rule() -> None:
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    eligibility = protocol["eligibility"]
    decision = protocol["decision_rule"]

    assert eligibility["required_test_gas"] == "hydrogen"
    assert eligibility["minimum_eligible_case_count"] == 18
    assert eligibility["minimum_usable_sensor_count_per_case"] == 8
    assert "overlap" in eligibility["overlap_rule"].lower()
    assert decision["all_screens_must_pass"] is True
    assert decision["parameter_tuning_after_access_permitted"] is False
    assert len(decision["screens"]) == 5
    assert protocol["runtime_policy"]["enabled"] is False
    assert protocol["runtime_policy"]["alarm_or_trip_setpoint_change_permitted"] is False


def test_oedi_source_is_rejected_before_numerical_access() -> None:
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    protocol = result["protocol"]
    source = result["source"]
    identity = result["identity_crosscheck"]
    eligibility = result["eligibility"]
    evaluation = result["model_evaluation"]

    assert protocol["sha256"] == _sha256(PROTOCOL)
    assert protocol["freeze_commit"].startswith("2aa686d")
    assert protocol["detailed_access_confirmed_after_freeze"] is True
    assert source["doi"] == "10.7799/17118570"
    assert source["test_gas"] == "helium surrogate"
    assert source["experiment_count"] == 5
    assert source["raw_archive_downloaded"] is False
    assert identity["source_doi_matches_legacy_development_source"] is True
    assert identity["independent_of_candidate_development"] is False
    assert eligibility["decision"] == "INELIGIBLE_NO_MODEL_EVALUATION"
    assert set(eligibility["failed_requirements"]) == {
        "actual_hydrogen_test_gas",
        "minimum_eligible_case_count",
        "independent_nonoverlap_with_candidate_development",
    }
    assert evaluation["executed"] is False
    assert evaluation["sensor_responses_opened"] is False
    assert evaluation["spatial_rank_metrics_computed"] is False
    assert result["gate_impact"][
        "h2safe_spatial_detector_transfer_validation"
    ] == "unchanged_fail"
