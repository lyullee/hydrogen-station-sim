from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULT = (
    ROOT
    / "research/woodfield_metal_tank_heat_transfer_development_2026_10_08.json"
)
RUNNER = ROOT / "scripts/run_woodfield_metal_tank_heat_transfer_development.py"


def test_woodfield_result_is_claim_bounded_and_source_pinned() -> None:
    report = json.loads(RESULT.read_text(encoding="utf-8"))

    assert report["artifact_type"] == (
        "post_access_woodfield_metal_tank_heat_transfer_development"
    )
    assert report["evidence_role"] == "model-development diagnostic only"
    assert report["post_access"] is True
    assert report["parameter_fitting"] is False
    assert report["runtime_parameter_updated"] is False
    assert report["validation_gate_effect"] == "none"
    assert report["source"]["commit"] == (
        "1040d758b819533451086baa5cf2a47b4292a22f"
    )
    assert report["source"]["source_hashes_match"] is True
    assert report["privacy_and_rights"]["raw_measurement_rows_persisted"] is False
    assert report["privacy_and_rights"]["raw_measurement_arrays_persisted"] is False
    assert report["privacy_and_rights"][
        "absolute_local_source_path_persisted"
    ] is False


def test_existing_mixed_convection_improves_fill_and_stays_off_in_discharge() -> None:
    report = json.loads(RESULT.read_text(encoding="utf-8"))
    comparison = report["comparisons"]
    interpretation = report["interpretation"]

    assert comparison["fill_pressure_rmse_reduction_percent"] > 20.0
    assert comparison["fill_temperature_envelope_rmse_reduction_percent"] > 60.0
    assert comparison["discharge_pressure_rmse_difference_bar"] == 0.0
    assert comparison["discharge_temperature_envelope_rmse_difference_k"] == 0.0
    assert interpretation["fill_mechanism_supported"] is True
    assert interpretation["discharge_path_unchanged_by_inlet_forcing"] is True
    assert interpretation["production_default_change_supported"] is False
    assert interpretation["prospective_validation_claim_supported"] is False
    runs = [
        run
        for experiment in report["experiments"].values()
        for run in experiment.values()
    ]
    assert max(run["mass_residual_relative"] for run in runs) < 1.0e-9
    assert max(run["energy_residual_relative"] for run in runs) < 1.0e-9


def test_committed_evidence_contains_no_private_absolute_path_or_raw_arrays() -> None:
    evidence_text = RESULT.read_text(encoding="utf-8").lower()
    runner_text = RUNNER.read_text(encoding="utf-8").lower()

    assert "c:\\\\users\\\\lyul" not in evidence_text
    assert "c:\\\\users\\\\lyul" not in runner_text
    assert '"time": [' not in evidence_text
    assert '"temp": [' not in evidence_text
    assert '"pres": [' not in evidence_text
