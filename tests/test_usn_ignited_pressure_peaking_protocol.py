import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_ignited_pressure_peaking_protocol_is_frozen_before_holdout_access():
    payload = json.loads(
        (ROOT / "research/usn_17934047_ignited_pressure_peaking_protocol_2026_10_08.json").read_text(
            encoding="utf-8"
        )
    )
    assert payload["status"] == "frozen_before_holdout_outcome_access"
    assert payload["cohort"]["expected_holdout_count"] == 28
    assert payload["cohort"]["development_only_cases"] == [29, 30, 31]
    assert payload["fixed_model"]["vent_discharge_coefficient"] == 0.9
    assert payload["fixed_model"]["enclosure_wall_heat_transfer_w_m2_k"] == 30.0
    assert payload["signal_processing"]["peak_window_s"] == [1.0, 12.0]
    assert payload["signal_processing"]["trace_sampling_hz"] == 100


def test_ignited_pressure_peaking_protocol_has_strict_claim_boundary_and_rule():
    payload = json.loads(
        (ROOT / "research/usn_17934047_ignited_pressure_peaking_protocol_2026_10_08.json").read_text(
            encoding="utf-8"
        )
    )
    assert payload["endpoints"]["primary"]["case_threshold_kpa"] == 2.0
    assert payload["decision_rule"]["minimum_eligible_cases"] == 20
    assert payload["decision_rule"]["primary_pass_fraction"] == 0.8
    boundary = payload["claim_boundary"].lower()
    assert "cannot validate" in boundary
    assert "saga effectiveness" in boundary
