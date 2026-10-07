from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np

import h2station.apparatus_release_validation as validation
from h2station.apparatus_release_validation import (
    ApparatusReleaseCaseResult,
    ApparatusReleaseTrace,
    evaluate_apparatus_release_case,
    load_apparatus_release_csv,
)
from scripts import run_apparatus_release_holdout as runner


ROOT = Path(__file__).resolve().parents[1]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _trace() -> ApparatusReleaseTrace:
    time_s = np.linspace(0.0, 1.0, 201)
    flow = np.sin(np.pi * time_s) * 0.02
    valve = np.clip(time_s / 0.1, 0.0, 1.0)
    return ApparatusReleaseTrace(
        time_s=time_s,
        source_pressure_pa_abs=np.linspace(20.0e6, 18.0e6, len(time_s)),
        source_temperature_k=np.linspace(300.0, 290.0, len(time_s)),
        line_pressure_pa_abs=np.linspace(101_325.0, 5.0e6, len(time_s)),
        line_temperature_k=np.linspace(293.15, 285.0, len(time_s)),
        terminal_mass_flow_kg_s=flow,
        valve_position_fraction=valve,
        source_mass_kg=np.linspace(1.0, 0.98, len(time_s)),
        ambient_pressure_pa=np.full(len(time_s), 101_325.0),
        ambient_temperature_k=np.full(len(time_s), 293.15),
    )


def _model_parameters() -> dict:
    return {
        "source_volume_m3": 0.025,
        "line_volume_m3": 0.0008,
        "upstream_diameter_m": 0.003,
        "terminal_diameter_m": 0.001,
        "valve_opening_time_s": 0.1,
    }


def _perfect_prediction(trace: ApparatusReleaseTrace) -> SimpleNamespace:
    n = len(trace.time_s)
    return SimpleNamespace(
        source_pressure_pa_abs=trace.source_pressure_pa_abs.copy(),
        line_pressure_pa_abs=trace.line_pressure_pa_abs.copy(),
        source_temperature_k=trace.source_temperature_k.copy(),
        line_temperature_k=trace.line_temperature_k.copy(),
        source_mass_kg=trace.source_mass_kg.copy(),
        line_mass_kg=np.full(n, 0.01),
        terminal_mass_flow_kg_s=trace.terminal_mass_flow_kg_s.copy(),
        valve_opening_fraction=trace.valve_position_fraction.copy(),
        cumulative_terminal_enthalpy_j=np.linspace(0.0, 100.0, n),
        cumulative_thermal_boundary_energy_j=np.zeros(n),
        mass_balance_residual_kg=np.zeros(n),
        energy_balance_residual_j=np.zeros(n),
    )


def _passing_result() -> ApparatusReleaseCaseResult:
    return ApparatusReleaseCaseResult(
        points=201,
        duration_s=1.0,
        sampling_hz_median=200.0,
        maximum_timestamp_jitter_s=0.0,
        source_pressure_nrmse_percent_initial=0.0,
        terminal_mass_flow_nrmse_percent_peak_measured=0.0,
        terminal_mass_flow_median_absolute_percentage_error_percent=0.0,
        half_peak_time_relative_error_percent=0.0,
        line_pressure_nrmse_percent_peak_measured=0.0,
        line_temperature_rmse_k=0.0,
        source_mass_nrmse_percent_initial=0.0,
        valve_position_rmse_fraction=0.0,
        mass_closure_max_relative_error=0.0,
        energy_closure_max_relative_error=0.0,
        measured_peak_mass_flow_kg_s=0.02,
        predicted_peak_mass_flow_kg_s=0.02,
        experimental_half_peak_time_s=0.83,
        predicted_half_peak_time_s=0.83,
        quality_gate_pass=True,
        primary_endpoint_pass=True,
        numerical_conservation_pass=True,
        joint_case_pass=True,
        gate_details={"all": True},
    )


def test_no_fit_case_evaluator_passes_identical_trace(monkeypatch):
    trace = _trace()
    monkeypatch.setattr(
        validation,
        "simulate_release_network",
        lambda _time, *, inputs: _perfect_prediction(trace),
    )

    result = evaluate_apparatus_release_case(
        trace, model_parameters=_model_parameters(),
    )

    assert result.quality_gate_pass is True
    assert result.primary_endpoint_pass is True
    assert result.numerical_conservation_pass is True
    assert result.joint_case_pass is True
    assert all(result.gate_details.values())


def test_csv_loader_requires_the_complete_synchronized_contract(tmp_path):
    path = tmp_path / "incomplete.csv"
    path.write_text("time_s,source_pressure_pa_abs\n0,1000000\n1,900000\n", encoding="utf-8")

    try:
        load_apparatus_release_csv(path)
    except ValueError as exc:
        assert "missing columns" in str(exc)
        assert "terminal_mass_flow_kg_s" in str(exc)
    else:
        raise AssertionError("incomplete trace must be rejected")


def test_campaign_runner_retains_cases_and_strips_private_paths(tmp_path, monkeypatch):
    raw_paths = []
    for index in range(8):
        path = tmp_path / f"private-facility-case-{index + 1}.csv"
        path.write_text("private raw placeholder\n", encoding="utf-8")
        raw_paths.append(path)
    monkeypatch.setattr(runner, "load_apparatus_release_csv", lambda _path: _trace())
    monkeypatch.setattr(
        runner,
        "evaluate_apparatus_release_case",
        lambda _trace_value, **_kwargs: _passing_result(),
    )
    cases = []
    for index, path in enumerate(raw_paths):
        cases.append({
            "case_id": f"AR-{index + 1:02d}",
            "data_file": str(path),
            "raw_data_sha256": _sha256(path),
            "strata": {
                "source_pressure_group": f"P{index // 4 + 1}",
                "geometry_group": f"G{(index // 2) % 2 + 1}",
                "valve_opening_group": f"V{index % 2 + 1}",
            },
        })
    manifest = {
        "schema_version": 1,
        "campaign_id": "anonymous-test",
        "protocol_sha256": _sha256(runner.PROTOCOL_PATH),
        "model_sha256": _sha256(runner.MODEL_PATH),
        "evaluator_sha256": _sha256(runner.EVALUATOR_PATH),
        "runner_sha256": _sha256(Path(runner.__file__).resolve()),
        "freeze": {
            "protocol_frozen_before_outcome_access": True,
            "model_frozen_before_outcome_access": True,
            "case_manifest_hashed_before_model_run": True,
            "post_freeze_parameter_tuning_prohibited": True,
            "failed_case_exclusion_prohibited": True,
        },
        "default_model_parameters": _model_parameters(),
        "cases": cases,
    }
    manifest_path = tmp_path / "private_manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    report = runner.run_campaign(manifest_path)
    encoded = json.dumps(report)

    assert report["decision"]["status"] == "PASS"
    assert report["aggregate"]["declared_cases"] == 8
    assert report["aggregate"]["joint_case_pass_fraction"] == 1.0
    assert report["privacy"]["raw_rows_persisted"] is False
    assert "private-facility" not in encoded
    assert "data_file" not in encoded
