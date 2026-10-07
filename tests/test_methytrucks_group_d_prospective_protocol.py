from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "research/methytrucks_group_d_prospective_protocol_2026_10_08.json"


def test_group_d_protocol_freezes_exact_unopened_workbook_and_thresholds() -> None:
    payload = json.loads(PROTOCOL.read_text(encoding="utf-8"))

    assert payload["status"] == "prospective_transient_protocol_frozen_before_workbook_access"
    assert payload["pre_access_attestation"]["selected_workbook_downloaded_before_freeze"] is False
    assert payload["pre_access_attestation"]["selected_workbook_opened_before_freeze"] is False
    assert payload["pre_access_attestation"]["bibliographic_event_summary_seen_before_freeze"] is True
    assert payload["frozen_selection"] == {
        "filename": "20241024_Test_5_SINTEF_CESAME.xlsx",
        "zenodo_file_size_bytes": 69408,
        "zenodo_md5": "e67b7cbf1cc4907ff6b460044b7b70b9",
        "selection_rule": (
            "Evaluate this exact file once. Retain an intake or model failure; do not replace it "
            "with the companion mass-summary workbook or another experiment."
        ),
        "case_count": 1,
    }
    assert payload["acceptance_criteria"] == {
        "pressure_rmse_mpa_max": 5.0,
        "temperature_rmse_c_max": 10.0,
        "pressure_final_absolute_error_mpa_max": 5.0,
        "temperature_peak_absolute_error_c_max": 10.0,
        "all_four_required": True,
    }
    assert payload["frozen_model"]["case_specific_fitting_allowed"] is False
    assert payload["frozen_model"]["time_warping_allowed"] is False
    assert payload["full_loop_gate_impact"]["can_close_full_loop_external_validation_alone"] is False


def test_group_d_protocol_forbids_geometry_inference_and_case_replacement() -> None:
    payload = json.loads(PROTOCOL.read_text(encoding="utf-8"))

    geometry_policy = payload["frozen_model"]["tank_geometry_policy"]
    assert "Do not infer volume" in geometry_policy
    assert "cannot change" in payload["decision_rule"]
    assert "INELIGIBLE_METADATA" in payload["measurement_only_intake"]["failure_rule"]
