from __future__ import annotations

import json

import numpy as np

from h2station.schefer_2007_nonadiabatic_diagnostic import (
    ScheferNonadiabaticDiagnosticMetrics,
    ScheferNonadiabaticDiagnosticParameters,
    evaluate_declared_sensitivity_envelope,
    write_diagnostic_json,
)
from h2station.schefer_2007_validation import Schefer2007PressureTrace


def test_parameter_geometry_is_explicitly_diagnostic_only():
    parameters = ScheferNonadiabaticDiagnosticParameters(1.0e6, 6.0)
    assert parameters.wall_mass_kg == 2000.0
    assert parameters.equivalent_internal_height_m > 0.0


def test_envelope_returns_full_grid_without_selection(monkeypatch):
    trace = Schefer2007PressureTrace(
        time_s=np.array([0.0, 1.0]),
        measured_pressure_psi=np.array([100.0, 90.0]),
    )

    def fake_evaluate(_trace, parameters):
        return ScheferNonadiabaticDiagnosticMetrics(
            wall_heat_capacity_j_k=parameters.wall_heat_capacity_j_k,
            external_heat_transfer_w_m2_k=parameters.external_heat_transfer_w_m2_k,
            pressure_nrmse_percent_initial_measured=0.0,
            median_absolute_percentage_error_percent=0.0,
            half_pressure_time_relative_error_percent=0.0,
            nrmse_screen_pass=True,
            median_ape_screen_pass=True,
            half_pressure_time_screen_pass=True,
            joint_primary_screen_pass=True,
        )

    monkeypatch.setattr(
        "h2station.schefer_2007_nonadiabatic_diagnostic.evaluate_sensitivity_point",
        fake_evaluate,
    )
    metrics = evaluate_declared_sensitivity_envelope(
        trace,
        wall_heat_capacities_j_k=(1.0, 2.0),
        external_heat_transfer_coefficients_w_m2_k=(3.0, 4.0, 5.0),
    )
    assert len(metrics) == 6
    assert {(item.wall_heat_capacity_j_k, item.external_heat_transfer_w_m2_k) for item in metrics} == {
        (1.0, 3.0), (1.0, 4.0), (1.0, 5.0),
        (2.0, 3.0), (2.0, 4.0), (2.0, 5.0),
    }


def test_diagnostic_artifact_keeps_promotion_guards(tmp_path):
    metrics = [
        ScheferNonadiabaticDiagnosticMetrics(
            wall_heat_capacity_j_k=1.0,
            external_heat_transfer_w_m2_k=2.0,
            pressure_nrmse_percent_initial_measured=1.0,
            median_absolute_percentage_error_percent=2.0,
            half_pressure_time_relative_error_percent=3.0,
            nrmse_screen_pass=True,
            median_ape_screen_pass=True,
            half_pressure_time_screen_pass=True,
            joint_primary_screen_pass=True,
        )
    ]
    output = tmp_path / "diagnostic.json"
    write_diagnostic_json(output, metrics)
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["status"] == "post_outcome_sensitivity_diagnostic_only"
    assert payload["model_changed"] is False
    assert payload["runtime_promotion"] is False
    assert payload["holdout_gate_promotion"] is False
