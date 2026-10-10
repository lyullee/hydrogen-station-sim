from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_geometry_resolved_followup_is_explicitly_non_validation() -> None:
    record = json.loads(
        (ROOT / "research/dickens_typeiii_geometry_resolved_followup_2026_10_10.json")
        .read_text(encoding="utf-8")
    )
    assert record["status"] == "candidate_protocol_input_not_validation"
    assert record["evidence_role"] == "post_outcome_model_development_diagnostic"
    assert record["source_geometry"]["inlet_pipe_internal_diameter_m"] == 0.005
    assert record["source_geometry"]["inlet_pipe_extension_m"] == 0.082
    assert record["selected_diagnostic"]["nozzle_diameter_mm"] == 5.0
    assert record["selected_diagnostic"]["joint_primary_screen_pass"] is True
    interpretation = record["diagnostic_interpretation"]
    assert interpretation["original_frozen_validation_result_changed"] is False
    assert interpretation["runtime_parameter_updated"] is False
    assert interpretation["validation_gate_effect"] == "none"
    assert interpretation["tank_length_mapping_resolved"] is False
    assert len(record["next_protocol_requirements"]) == 4
