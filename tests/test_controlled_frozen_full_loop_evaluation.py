import csv
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import evaluate_controlled_full_loop as evaluator  # noqa: E402


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _protocol(trace_sha256: str) -> dict:
    return {
        "schema_version": 1,
        "artifact_type": "controlled_hrs_frozen_evaluation_protocol",
        "frozen_before_outcomes": True,
        "model_commit": "frozen-test-commit",
        "expected_trace_sha256": trace_sha256,
        "evaluation_scope": "cascade_resolved_station_to_vehicle",
        "ambient_temperature_c": 25.0,
        "vehicle": {
            "initial_state_policy": "trace_first_sample",
            "internal_volume_m3": 0.12,
            "nominal_working_pressure_mpa": 70.0,
        },
        "control": {
            "target_pressure_mpa": 70.0,
            "pressure_ramp_rate_mpa_min": 10.0,
            "delivery_temperature_c": -40.0,
            "maximum_gas_temperature_c": 85.0,
            "maximum_mass_flow_g_s": 60.0,
            "control_period_s": 1.0,
        },
        "station": {
            "pressure_observable": "hose_pressure",
            "initial_bank_pressure_mpa": {
                "low": 45.0,
                "medium": 65.0,
                "high": 95.0,
            },
        },
        "process": {
            "recharge_enabled": False,
            "recharge_auto_stop": True,
            "trailer_pressure_mpa": 20.0,
            "trailer_temperature_c": 25.0,
            "trailer_capacity_kg": 200.0,
        },
        "state_semantics": {
            "cascade_selected_bank": {
                "low": ["low"],
                "medium": ["medium"],
                "high": ["high"],
            },
            "compressor_active_values": ["running"],
        },
        "acceptance_criteria": {
            "pressure_rmse_mpa_max": 0.001,
            "temperature_rmse_c_max": 0.001,
            "mass_flow_rmse_g_s_max": 0.001,
            "selected_source_pressure_rmse_mpa_max": 0.001,
            "delivered_temperature_rmse_c_max": 0.001,
            "station_pressure_rmse_mpa_max": 0.001,
            "cascade_bank_pressure_rmse_mpa_max": 0.001,
            "dispatch_accuracy_min": 1.0,
            "compressor_state_accuracy_min": 1.0,
        },
    }


def _synthetic_trace() -> list[dict[str, str]]:
    frozen = evaluator.FrozenProtocol(
        payload={},
        scope="cascade_resolved_station_to_vehicle",
        vehicle_volume_m3=0.12,
        vehicle_nominal_pressure_mpa=70.0,
        ambient_temperature_c=25.0,
        target_pressure_mpa=70.0,
        pressure_ramp_rate_mpa_min=10.0,
        delivery_temperature_c=-40.0,
        maximum_gas_temperature_c=85.0,
        maximum_mass_flow_g_s=60.0,
        control_period_s=1.0,
        initial_bank_pressure_mpa={"low": 45.0, "medium": 65.0, "high": 95.0},
        recharge_enabled=False,
        recharge_auto_stop=True,
        trailer_pressure_mpa=20.0,
        trailer_temperature_c=25.0,
        trailer_capacity_kg=200.0,
        station_pressure_observable="hose_pressure",
        selected_bank_values={"low": frozenset({"low"}), "medium": frozenset({"medium"}), "high": frozenset({"high"})},
        compressor_active_values=frozenset({"running"}),
        criteria={},
    )
    times = np.arange(20, dtype=float)
    seed = [{"vehicle_pressure_mpa_abs": "5", "temperature_degC": "25"} for _ in times]
    _, samples = evaluator._simulate(seed, times, frozen)
    rows = []
    for sample in samples:
        selected = sample.dispatch_bank or "off"
        source_pressure = sample.bank_pressure_pa.get(sample.dispatch_bank or "low", 0.0) / 1.0e6
        rows.append({
            "time_s": f"{sample.time_s:.9f}",
            "vehicle_pressure_mpa_abs": f"{sample.vehicle_pressure_pa / 1.0e6:.12f}",
            "temperature_degC": f"{sample.vehicle_temperature_k - 273.15:.12f}",
            "mass_flow_g_s": f"{sample.nozzle_mass_flow_kg_s * 1000.0:.12f}",
            "station_pressure_mpa_abs": f"{sample.hose_pressure_pa / 1.0e6:.12f}",
            "delivered_gas_temperature_degC": f"{sample.precooler_outlet_temperature_k - 273.15:.12f}",
            "cascade_source_pressure_mpa_abs": f"{source_pressure:.12f}",
            "cascade_low_pressure_mpa_abs": f"{sample.bank_pressure_pa['low'] / 1.0e6:.12f}",
            "cascade_medium_pressure_mpa_abs": f"{sample.bank_pressure_pa['medium'] / 1.0e6:.12f}",
            "cascade_high_pressure_mpa_abs": f"{sample.bank_pressure_pa['high'] / 1.0e6:.12f}",
            "cascade_selected_bank": selected,
            "compressor_state": "running" if sample.recharge_bank else "idle",
            "precooler_state": "ready",
            "leak_check_state": "passed",
            "vent_state": "closed",
            "fault_state": "none",
            "esd_state": "armed",
        })
    return rows


def _write_trace(path: Path) -> None:
    rows = _synthetic_trace()
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _write_receipt(path: Path, trace_path: Path) -> None:
    path.write_text(json.dumps({
        "trace_sha256": _hash(trace_path),
        "station_to_vehicle_trace_ready": True,
        "cascade_dispatch_evaluable": True,
        "full_loop_trace_ready": True,
        "evaluation_scope": "cascade_resolved_station_to_vehicle",
    }), encoding="utf-8")


def test_evaluates_hash_locked_full_loop_without_persisting_rows(tmp_path, monkeypatch):
    trace_path = tmp_path / "controlled.csv"
    receipt_path = tmp_path / "receipt.json"
    protocol_path = tmp_path / "frozen_protocol.json"
    _write_trace(trace_path)
    _write_receipt(receipt_path, trace_path)
    protocol_path.write_text(json.dumps(_protocol(_hash(trace_path))), encoding="utf-8")
    monkeypatch.setattr(evaluator, "_git_commit", lambda: "frozen-test-commit")
    monkeypatch.setattr(evaluator, "_worktree_clean", lambda: True)

    result = evaluator.evaluate(trace_path, receipt_path, protocol_path)

    assert result["decision"] == "FROZEN_EVALUATION_PASS"
    assert result["evaluation_scope"] == "cascade_resolved_station_to_vehicle"
    assert result["raw_rows_persisted"] is False
    assert result["state_metrics"]["selected_bank"]["accuracy"] == 1.0
    assert result["metrics"]["vehicle_pressure_mpa"]["rmse"] < 1e-6


def test_rejects_trace_substitution_before_model_execution(tmp_path, monkeypatch):
    trace_path = tmp_path / "controlled.csv"
    receipt_path = tmp_path / "receipt.json"
    protocol_path = tmp_path / "frozen_protocol.json"
    _write_trace(trace_path)
    _write_receipt(receipt_path, trace_path)
    protocol_path.write_text(json.dumps(_protocol("0" * 64)), encoding="utf-8")
    monkeypatch.setattr(evaluator, "_git_commit", lambda: "frozen-test-commit")
    monkeypatch.setattr(evaluator, "_worktree_clean", lambda: True)

    with pytest.raises(ValueError, match="expected_trace_sha256"):
        evaluator.evaluate(trace_path, receipt_path, protocol_path)
