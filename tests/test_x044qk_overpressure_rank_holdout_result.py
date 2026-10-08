import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _json(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def test_x044qk_holdout_preserves_freeze_and_fails_closed() -> None:
    protocol_path = ROOT / "research/x044qk_overpressure_rank_holdout_protocol_2026_10_08.json"
    protocol = _json("research/x044qk_overpressure_rank_holdout_protocol_2026_10_08.json")
    result = _json("research/x044qk_overpressure_rank_holdout_result_2026_10_08.json")

    assert hashlib.sha256(protocol_path.read_bytes()).hexdigest() == result[
        "freeze_integrity"
    ]["protocol_sha256"]
    assert protocol["status"] == "FROZEN_BEFORE_RAW_PRESSURE_OUTCOME_ACCESS"
    assert protocol["selection_rule"]["selected_experiment_numbers"] == [1, 2, 3, 18, 19, 20]
    assert result["decision"] == (
        "MODEL_SCREEN_NOT_RUN_INELIGIBLE_UNCALIBRATED_PRESSURE_VOLTAGE"
    )
    assert result["early_intake_check"]["schema"]["dynamic_pressure_channel_count"] == 4
    assert set(result["early_intake_check"]["schema"]["dynamic_pressure_units"]) == {"V"}
    assert result["early_intake_check"]["outcome_window_opened"] is False
    assert result["eligibility"]["engineering_pressure_units_present"] is False
    assert result["eligibility"][
        "publisher_documented_voltage_to_pressure_calibration_present"
    ] is False
    assert result["execution"]["hyram_model_executed"] is False
    assert result["execution"]["primary_metrics_computed"] is False
    assert result["execution"]["runtime_parameter_updated"] is False
    assert result["execution"]["validation_gate_effect"] == "none"


def test_x044qk_holdout_claim_remains_bounded() -> None:
    result = _json("research/x044qk_overpressure_rank_holdout_result_2026_10_08.json")
    boundary = result["claim_boundary"].lower()

    for phrase in (
        "not a numerical hyram failure",
        "does not validate",
        "full digital twin",
        "regulatory compliance",
    ):
        assert phrase in boundary
