"""Evaluate one controlled HRS trace against a pre-frozen model protocol.

The evaluator consumes only a de-identified trace produced by the controlled
exporters.  It does not fit parameters, alter an input, interpolate an
observation, or copy a row-level trace into the repository.  Its protocol,
trace, receipt, and result must all remain outside the Git worktree.

This is intentionally stricter than a model demonstration.  The protocol
locks the exact trace digest, source commit, vehicle/station boundary values,
state semantics, and pass thresholds before numerical outcomes are read.  A
pass is a bounded evaluation result only; it is not safety certification or a
claim that every IJHE evidence gate has closed.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import subprocess
from typing import Any, Iterable

import numpy as np

from h2station.api import ProcessSettings
from h2station.operations import ProcessRuntime
from h2station.risk.runtime_backend import UnavailableHyRAMBackend
from h2station.safe_operation import SafeOperationSample
from h2station.scenario import (
    BANK_REFERENCE_MAX_PRESSURE_PA,
    ReferenceScenario,
    build_reference_scenario,
)


ROOT = Path(__file__).resolve().parents[1]
_SCOPES = frozenset({
    "station_to_vehicle_selected_bank_only",
    "cascade_resolved_station_to_vehicle",
})
_BANKS = ("low", "medium", "high")
_NUMERIC_TRACE_COLUMNS = (
    "time_s",
    "vehicle_pressure_mpa_abs",
    "temperature_degC",
    "mass_flow_g_s",
    "station_pressure_mpa_abs",
    "delivered_gas_temperature_degC",
    "cascade_source_pressure_mpa_abs",
)
_STATE_TRACE_COLUMNS = (
    "cascade_selected_bank",
    "compressor_state",
    "precooler_state",
    "leak_check_state",
    "vent_state",
    "fault_state",
    "esd_state",
)
_BANK_TRACE_COLUMNS = tuple(f"cascade_{bank}_pressure_mpa_abs" for bank in _BANKS)


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _outside_repository(path: Path, *, field: str) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError:
        return resolved
    raise ValueError(f"{field} must be outside the repository worktree")


def _git_commit() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True,
            capture_output=True, text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unavailable"


def _worktree_clean() -> bool | None:
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"], cwd=ROOT, check=True,
            capture_output=True, text=True,
        )
        return not bool(result.stdout.strip())
    except (OSError, subprocess.CalledProcessError):
        return None


def _finite(value: object, *, field: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be numeric") from exc
    if not math.isfinite(number):
        raise ValueError(f"{field} must be finite")
    return number


def _positive(value: object, *, field: str) -> float:
    number = _finite(value, field=field)
    if number <= 0.0:
        raise ValueError(f"{field} must be positive")
    return number


def _mapping(value: object, *, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{field} must be an object")
    return value


def _normalized_values(value: object, *, field: str) -> frozenset[str]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{field} must be a nonempty list")
    normalized = {
        item.strip().casefold()
        for item in value
        if isinstance(item, str) and item.strip()
    }
    if not normalized:
        raise ValueError(f"{field} must contain nonempty strings")
    return frozenset(normalized)


def _read_trace(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        header = tuple(reader.fieldnames or ())
        missing = [
            name for name in (*_NUMERIC_TRACE_COLUMNS, *_STATE_TRACE_COLUMNS)
            if name not in header
        ]
        if missing:
            raise ValueError("trace is missing canonical channels: " + ", ".join(missing))
        rows = list(reader)
    if len(rows) < 20:
        raise ValueError("trace requires at least 20 rows")
    return rows


def _times(rows: list[dict[str, str]]) -> np.ndarray:
    values = np.asarray([
        _finite(row.get("time_s", ""), field=f"trace time_s row {index}")
        for index, row in enumerate(rows, start=2)
    ], dtype=float)
    if abs(values[0]) > 1.0e-9:
        raise ValueError("controlled trace must use relative time beginning at zero")
    if np.any(np.diff(values) <= 0.0):
        raise ValueError("controlled trace time_s must be strictly increasing")
    return values


def _trace_vector(rows: list[dict[str, str]], column: str) -> np.ndarray:
    return np.asarray([
        _finite(row.get(column, ""), field=f"trace {column} row {index}")
        for index, row in enumerate(rows, start=2)
    ], dtype=float)


def _optional_trace_vector(rows: list[dict[str, str]], column: str) -> np.ndarray | None:
    values: list[float] = []
    for index, row in enumerate(rows, start=2):
        raw = row.get(column, "")
        if raw is None or not str(raw).strip():
            return None
        values.append(_finite(raw, field=f"trace {column} row {index}"))
    return np.asarray(values, dtype=float)


def _metric(observed: np.ndarray, predicted: np.ndarray) -> dict[str, float | int]:
    if observed.size == 0 or predicted.size != observed.size:
        raise ValueError("metric requires equal nonempty observed and predicted vectors")
    error = predicted - observed
    return {
        "sample_count": int(observed.size),
        "rmse": float(np.sqrt(np.mean(error ** 2))),
        "mae": float(np.mean(np.abs(error))),
        "final_error": float(error[-1]),
        "maximum_absolute_error": float(np.max(np.abs(error))),
    }


def _state_accuracy(observed: Iterable[str | None], predicted: Iterable[str | None]) -> dict[str, int | float]:
    pairs = [
        (left, right)
        for left, right in zip(observed, predicted)
        if left is not None
    ]
    if not pairs:
        raise ValueError("state metric has no comparable samples")
    return {
        "sample_count": len(pairs),
        "accuracy": float(sum(left == right for left, right in pairs) / len(pairs)),
    }


def _model_index(times: np.ndarray, source_times: np.ndarray) -> np.ndarray:
    right = np.searchsorted(source_times, times, side="left")
    right = np.clip(right, 0, len(source_times) - 1)
    left = np.clip(right - 1, 0, len(source_times) - 1)
    choose_left = np.abs(source_times[left] - times) <= np.abs(source_times[right] - times)
    return np.where(choose_left, left, right)


@dataclass(frozen=True)
class FrozenProtocol:
    payload: dict[str, Any]
    scope: str
    vehicle_volume_m3: float
    vehicle_nominal_pressure_mpa: float
    ambient_temperature_c: float
    target_pressure_mpa: float
    pressure_ramp_rate_mpa_min: float
    delivery_temperature_c: float
    maximum_gas_temperature_c: float
    maximum_mass_flow_g_s: float
    control_period_s: float
    initial_bank_pressure_mpa: dict[str, float]
    recharge_enabled: bool
    recharge_auto_stop: bool
    trailer_pressure_mpa: float
    trailer_temperature_c: float
    trailer_capacity_kg: float
    station_pressure_observable: str
    selected_bank_values: dict[str, frozenset[str]]
    compressor_active_values: frozenset[str]
    criteria: dict[str, float]


def _protocol(payload: dict[str, Any], *, trace_sha256: str, receipt: dict[str, Any]) -> FrozenProtocol:
    if payload.get("schema_version") != 1:
        raise ValueError("protocol schema_version must be 1")
    if payload.get("artifact_type") != "controlled_hrs_frozen_evaluation_protocol":
        raise ValueError("protocol artifact_type is invalid")
    if payload.get("frozen_before_outcomes") is not True:
        raise ValueError("protocol must attest frozen_before_outcomes true")
    if payload.get("model_commit") != _git_commit():
        raise ValueError("protocol model_commit does not match the checked-out model")
    if _worktree_clean() is not True:
        raise RuntimeError("controlled evaluation requires a clean source worktree")
    if payload.get("expected_trace_sha256") != trace_sha256:
        raise ValueError("protocol expected_trace_sha256 does not match the controlled trace")
    scope = payload.get("evaluation_scope")
    if scope not in _SCOPES:
        raise ValueError("protocol evaluation_scope is unsupported")
    if receipt.get("evaluation_scope") != scope:
        raise ValueError("receipt evaluation_scope does not match the frozen protocol")
    if receipt.get("trace_sha256") != trace_sha256:
        raise ValueError("receipt trace_sha256 does not match the controlled trace")
    if not receipt.get("station_to_vehicle_trace_ready"):
        raise ValueError("receipt has not passed the station-to-vehicle trace screen")
    if scope == "cascade_resolved_station_to_vehicle" and not receipt.get("full_loop_trace_ready"):
        raise ValueError("receipt is not cascade-resolved full-loop ready")
    if scope == "station_to_vehicle_selected_bank_only" and receipt.get("cascade_dispatch_evaluable"):
        raise ValueError("cascade-resolved receipt must use the cascade-resolved protocol scope")

    vehicle = _mapping(payload.get("vehicle"), field="protocol.vehicle")
    if vehicle.get("initial_state_policy") != "trace_first_sample":
        raise ValueError("vehicle.initial_state_policy must be trace_first_sample")
    control = _mapping(payload.get("control"), field="protocol.control")
    station = _mapping(payload.get("station"), field="protocol.station")
    process = _mapping(payload.get("process"), field="protocol.process")
    states = _mapping(payload.get("state_semantics"), field="protocol.state_semantics")
    criteria_raw = _mapping(payload.get("acceptance_criteria"), field="protocol.acceptance_criteria")

    initial_banks_raw = _mapping(
        station.get("initial_bank_pressure_mpa"), field="protocol.station.initial_bank_pressure_mpa",
    )
    initial_banks = {
        bank: _positive(initial_banks_raw.get(bank), field=f"initial {bank} bank pressure")
        for bank in _BANKS
    }
    for bank, maximum_pa in zip(_BANKS, BANK_REFERENCE_MAX_PRESSURE_PA):
        if initial_banks[bank] > maximum_pa / 1.0e6:
            raise ValueError(f"initial {bank} bank pressure exceeds its declared model maximum")

    selected_raw = _mapping(states.get("cascade_selected_bank"), field="state_semantics.cascade_selected_bank")
    selected = {
        bank: _normalized_values(selected_raw.get(bank), field=f"selected-bank values for {bank}")
        for bank in _BANKS
    }
    combined = set().union(*selected.values())
    if sum(len(values) for values in selected.values()) != len(combined):
        raise ValueError("selected-bank state values must map to only one bank")

    required_criteria = {
        "pressure_rmse_mpa_max",
        "temperature_rmse_c_max",
        "mass_flow_rmse_g_s_max",
        "selected_source_pressure_rmse_mpa_max",
        "delivered_temperature_rmse_c_max",
    }
    if scope == "cascade_resolved_station_to_vehicle":
        required_criteria.update({
            "cascade_bank_pressure_rmse_mpa_max",
            "dispatch_accuracy_min",
            "compressor_state_accuracy_min",
        })
    if station.get("pressure_observable") != "not_evaluated":
        required_criteria.add("station_pressure_rmse_mpa_max")
    criteria = {
        key: _positive(criteria_raw.get(key), field=f"acceptance criterion {key}")
        for key in required_criteria
    }
    for key in ("dispatch_accuracy_min", "compressor_state_accuracy_min"):
        if key in criteria and criteria[key] > 1.0:
            raise ValueError(f"acceptance criterion {key} cannot exceed 1")

    station_pressure_observable = station.get("pressure_observable")
    if station_pressure_observable not in {"hose_pressure", "not_evaluated"}:
        raise ValueError("station.pressure_observable must be hose_pressure or not_evaluated")
    recharge_enabled = process.get("recharge_enabled")
    if not isinstance(recharge_enabled, bool):
        raise ValueError("process.recharge_enabled must be boolean")
    recharge_auto_stop = process.get("recharge_auto_stop")
    if not isinstance(recharge_auto_stop, bool):
        raise ValueError("process.recharge_auto_stop must be boolean")

    return FrozenProtocol(
        payload=payload,
        scope=scope,
        vehicle_volume_m3=_positive(vehicle.get("internal_volume_m3"), field="vehicle.internal_volume_m3"),
        vehicle_nominal_pressure_mpa=_positive(vehicle.get("nominal_working_pressure_mpa"), field="vehicle.nominal_working_pressure_mpa"),
        ambient_temperature_c=_finite(payload.get("ambient_temperature_c"), field="ambient_temperature_c"),
        target_pressure_mpa=_positive(control.get("target_pressure_mpa"), field="control.target_pressure_mpa"),
        pressure_ramp_rate_mpa_min=_positive(control.get("pressure_ramp_rate_mpa_min"), field="control.pressure_ramp_rate_mpa_min"),
        delivery_temperature_c=_finite(control.get("delivery_temperature_c"), field="control.delivery_temperature_c"),
        maximum_gas_temperature_c=_positive(control.get("maximum_gas_temperature_c"), field="control.maximum_gas_temperature_c"),
        maximum_mass_flow_g_s=_positive(control.get("maximum_mass_flow_g_s"), field="control.maximum_mass_flow_g_s"),
        control_period_s=_positive(control.get("control_period_s"), field="control.control_period_s"),
        initial_bank_pressure_mpa=initial_banks,
        recharge_enabled=recharge_enabled,
        recharge_auto_stop=recharge_auto_stop,
        trailer_pressure_mpa=_positive(process.get("trailer_pressure_mpa"), field="process.trailer_pressure_mpa"),
        trailer_temperature_c=_finite(process.get("trailer_temperature_c"), field="process.trailer_temperature_c"),
        trailer_capacity_kg=_positive(process.get("trailer_capacity_kg"), field="process.trailer_capacity_kg"),
        station_pressure_observable=station_pressure_observable,
        selected_bank_values=selected,
        compressor_active_values=_normalized_values(
            states.get("compressor_active_values"), field="state_semantics.compressor_active_values",
        ),
        criteria=criteria,
    )


def _selected_bank(value: str, semantics: dict[str, frozenset[str]]) -> str | None:
    normalized = value.strip().casefold()
    for bank, values in semantics.items():
        if normalized in values:
            return bank
    return None


def _simulate(
    rows: list[dict[str, str]], times: np.ndarray, protocol: FrozenProtocol,
) -> tuple[Any, list[SafeOperationSample]]:
    initial_pressure = _finite(rows[0]["vehicle_pressure_mpa_abs"], field="initial vehicle pressure")
    initial_temperature = _finite(rows[0]["temperature_degC"], field="initial vehicle temperature")
    fill_percent = tuple(
        100.0 * protocol.initial_bank_pressure_mpa[bank] / (maximum_pa / 1.0e6)
        for bank, maximum_pa in zip(_BANKS, BANK_REFERENCE_MAX_PRESSURE_PA)
    )
    config = ReferenceScenario(
        duration_s=float(times[-1]),
        control_period_s=protocol.control_period_s,
        ambient_temperature_k=protocol.ambient_temperature_c + 273.15,
        initial_vehicle_pressure_pa=initial_pressure * 1.0e6,
        initial_vehicle_temperature_k=initial_temperature + 273.15,
        vehicle_internal_volume_m3=protocol.vehicle_volume_m3,
        vehicle_nominal_working_pressure_pa=protocol.vehicle_nominal_pressure_mpa * 1.0e6,
        target_vehicle_pressure_pa=protocol.target_pressure_mpa * 1.0e6,
        average_pressure_ramp_rate_pa_s=protocol.pressure_ramp_rate_mpa_min * 1.0e6 / 60.0,
        delivery_temperature_k=protocol.delivery_temperature_c + 273.15,
        maximum_gas_temperature_k=protocol.maximum_gas_temperature_c + 273.15,
        maximum_mass_flow_kg_s=protocol.maximum_mass_flow_g_s / 1000.0,
        compressor_suction_pressure_pa=protocol.trailer_pressure_mpa * 1.0e6,
        compressor_suction_temperature_k=protocol.trailer_temperature_c + 273.15,
        initial_bank_fill_percent=fill_percent,
        risk_update_period_s=float(times[-1]) + 1.0,
    )
    built = build_reference_scenario(config, UnavailableHyRAMBackend())
    settings = ProcessSettings(
        vehicle_1=True,
        vehicle_1_auto_stop=True,
        vehicle_1_target_pressure_mpa=protocol.target_pressure_mpa,
        pressure_recharge=protocol.recharge_enabled,
        trailer_supply=protocol.recharge_enabled,
        recharge_auto_stop=protocol.recharge_auto_stop,
        trailer_pressure_mpa=protocol.trailer_pressure_mpa,
        trailer_temperature_c=protocol.trailer_temperature_c,
        trailer_capacity_kg=protocol.trailer_capacity_kg,
    ).model_dump()
    built.simulator.process_runtime = ProcessRuntime(settings)
    samples: list[SafeOperationSample] = []
    trajectory = built.simulator.simulate(
        built.initial_state,
        float(times[-1]),
        protocol.control_period_s,
        pace_idle=False,
        sample_callback=samples.append,
    )
    if len(samples) < 2:
        raise RuntimeError("model returned insufficient samples for controlled evaluation")
    return trajectory, samples


def _prediction_arrays(samples: list[SafeOperationSample]) -> dict[str, Any]:
    return {
        "time_s": np.asarray([sample.time_s for sample in samples], dtype=float),
        "vehicle_pressure_mpa": np.asarray([sample.vehicle_pressure_pa / 1.0e6 for sample in samples]),
        "temperature_c": np.asarray([sample.vehicle_temperature_k - 273.15 for sample in samples]),
        "mass_flow_g_s": np.asarray([1000.0 * sample.nozzle_mass_flow_kg_s for sample in samples]),
        "hose_pressure_mpa": np.asarray([sample.hose_pressure_pa / 1.0e6 for sample in samples]),
        "delivered_temperature_c": np.asarray([sample.precooler_outlet_temperature_k - 273.15 for sample in samples]),
        "bank_pressure_mpa": {
            bank: np.asarray([sample.bank_pressure_pa[bank] / 1.0e6 for sample in samples])
            for bank in _BANKS
        },
        "dispatch_bank": [sample.dispatch_bank for sample in samples],
        "compressor_active": [sample.recharge_bank is not None for sample in samples],
    }


def _interpolate(times: np.ndarray, prediction: dict[str, Any], key: str) -> np.ndarray:
    return np.interp(times, prediction["time_s"], prediction[key])


def evaluate(
    trace_path: Path,
    receipt_path: Path,
    protocol_path: Path,
) -> dict[str, Any]:
    """Evaluate and return aggregates only; callers decide where to save them."""

    trace_path = _outside_repository(trace_path, field="controlled trace")
    receipt_path = _outside_repository(receipt_path, field="controlled receipt")
    protocol_path = _outside_repository(protocol_path, field="frozen evaluation protocol")
    trace_sha256 = _sha256(trace_path)
    receipt = _json(receipt_path)
    protocol = _protocol(_json(protocol_path), trace_sha256=trace_sha256, receipt=receipt)
    rows = _read_trace(trace_path)
    times = _times(rows)
    trajectory, samples = _simulate(rows, times, protocol)
    prediction = _prediction_arrays(samples)

    metrics: dict[str, dict[str, float | int]] = {
        "vehicle_pressure_mpa": _metric(
            _trace_vector(rows, "vehicle_pressure_mpa_abs"),
            _interpolate(times, prediction, "vehicle_pressure_mpa"),
        ),
        "vehicle_temperature_c": _metric(
            _trace_vector(rows, "temperature_degC"),
            _interpolate(times, prediction, "temperature_c"),
        ),
        "mass_flow_g_s": _metric(
            _trace_vector(rows, "mass_flow_g_s"),
            _interpolate(times, prediction, "mass_flow_g_s"),
        ),
        "delivered_temperature_c": _metric(
            _trace_vector(rows, "delivered_gas_temperature_degC"),
            _interpolate(times, prediction, "delivered_temperature_c"),
        ),
    }

    selected = [
        _selected_bank(row["cascade_selected_bank"], protocol.selected_bank_values)
        for row in rows
    ]
    selected_mask = np.asarray([value is not None for value in selected], dtype=bool)
    if not np.any(selected_mask):
        raise ValueError("no selected-bank trace state matches the frozen state semantics")
    observed_source = _trace_vector(rows, "cascade_source_pressure_mpa_abs")[selected_mask]
    predicted_source = np.asarray([
        np.interp(time, prediction["time_s"], prediction["bank_pressure_mpa"][bank])
        for time, bank in zip(times[selected_mask], np.asarray(selected, dtype=object)[selected_mask])
    ])
    metrics["selected_source_pressure_mpa"] = _metric(observed_source, predicted_source)

    if protocol.station_pressure_observable == "hose_pressure":
        metrics["station_pressure_mpa"] = _metric(
            _trace_vector(rows, "station_pressure_mpa_abs"),
            _interpolate(times, prediction, "hose_pressure_mpa"),
        )

    state_metrics: dict[str, dict[str, int | float]] = {}
    nearest = _model_index(times, prediction["time_s"])
    if protocol.scope == "cascade_resolved_station_to_vehicle":
        for bank, column in zip(_BANKS, _BANK_TRACE_COLUMNS):
            observed = _optional_trace_vector(rows, column)
            if observed is None:
                raise ValueError(f"cascade-resolved trace has no finite {column} values")
            metrics[f"cascade_{bank}_pressure_mpa"] = _metric(
                observed,
                np.interp(times, prediction["time_s"], prediction["bank_pressure_mpa"][bank]),
            )
        state_metrics["selected_bank"] = _state_accuracy(
            selected,
            [prediction["dispatch_bank"][index] for index in nearest],
        )
        compressor_observed = [
            row["compressor_state"].strip().casefold() in protocol.compressor_active_values
            for row in rows
        ]
        state_metrics["compressor_active"] = _state_accuracy(
            compressor_observed,
            [prediction["compressor_active"][index] for index in nearest],
        )

    decisions = {
        "vehicle_pressure_mpa": metrics["vehicle_pressure_mpa"]["rmse"] <= protocol.criteria["pressure_rmse_mpa_max"],
        "vehicle_temperature_c": metrics["vehicle_temperature_c"]["rmse"] <= protocol.criteria["temperature_rmse_c_max"],
        "mass_flow_g_s": metrics["mass_flow_g_s"]["rmse"] <= protocol.criteria["mass_flow_rmse_g_s_max"],
        "selected_source_pressure_mpa": metrics["selected_source_pressure_mpa"]["rmse"] <= protocol.criteria["selected_source_pressure_rmse_mpa_max"],
        "delivered_temperature_c": metrics["delivered_temperature_c"]["rmse"] <= protocol.criteria["delivered_temperature_rmse_c_max"],
    }
    if "station_pressure_mpa" in metrics:
        decisions["station_pressure_mpa"] = metrics["station_pressure_mpa"]["rmse"] <= protocol.criteria["station_pressure_rmse_mpa_max"]
    if protocol.scope == "cascade_resolved_station_to_vehicle":
        decisions["cascade_low_pressure_mpa"] = metrics["cascade_low_pressure_mpa"]["rmse"] <= protocol.criteria["cascade_bank_pressure_rmse_mpa_max"]
        decisions["cascade_medium_pressure_mpa"] = metrics["cascade_medium_pressure_mpa"]["rmse"] <= protocol.criteria["cascade_bank_pressure_rmse_mpa_max"]
        decisions["cascade_high_pressure_mpa"] = metrics["cascade_high_pressure_mpa"]["rmse"] <= protocol.criteria["cascade_bank_pressure_rmse_mpa_max"]
        decisions["selected_bank"] = state_metrics["selected_bank"]["accuracy"] >= protocol.criteria["dispatch_accuracy_min"]
        decisions["compressor_active"] = state_metrics["compressor_active"]["accuracy"] >= protocol.criteria["compressor_state_accuracy_min"]

    return {
        "schema_version": 1,
        "artifact_type": "controlled_hrs_frozen_evaluation_result",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "decision": "FROZEN_EVALUATION_PASS" if all(decisions.values()) else "FROZEN_EVALUATION_FAIL",
        "evaluation_scope": protocol.scope,
        "trace_sha256": trace_sha256,
        "receipt_sha256": _sha256(receipt_path),
        "protocol_sha256": _sha256(protocol_path),
        "source_commit": _git_commit(),
        "source_worktree_clean": True,
        "model_sample_count": len(samples),
        "observed_sample_count": len(rows),
        "simulation_stop_reason": trajectory.fueling_commands[-1].stop_reason if trajectory.fueling_commands else None,
        "metrics": metrics,
        "state_metrics": state_metrics,
        "acceptance_criteria": protocol.criteria,
        "acceptance_by_metric": decisions,
        "raw_rows_persisted": False,
        "source_identifiers_published": False,
        "absolute_timestamps_published": False,
        "claim_boundary": (
            "A pass compares one hash-locked, controlled trace to one frozen model "
            "configuration. It is not a safety certification, does not validate unmeasured "
            "phenomena, and does not by itself close the IJHE readiness gates."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trace", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = _outside_repository(args.output, field="controlled evaluation output")
    if output.exists():
        raise FileExistsError("controlled evaluation output must not already exist")
    result = evaluate(args.trace, args.receipt, args.protocol)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "decision": result["decision"],
        "evaluation_scope": result["evaluation_scope"],
        "output": str(output),
    }, ensure_ascii=False))
    return 0 if result["decision"] == "FROZEN_EVALUATION_PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
