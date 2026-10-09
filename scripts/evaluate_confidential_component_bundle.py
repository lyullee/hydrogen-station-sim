"""Replay a de-identified station/dispenser component bundle.

The exporter intentionally produces a small generic bundle outside the Git
worktree.  This evaluator is the next step after intake: it checks the
measured channels against fixed process envelopes and feeds the measured
pressure/temperature boundary into the frozen runtime.  It reports whether
the runtime can execute the boundary replay and what protection outcomes were
observed.

This is *not* a predictive accuracy test.  The measured boundary is an
exogenous input to the replay, no parameter is fitted, and no outcome is used
to alter the model.  The result therefore cannot establish station-to-vehicle
accuracy, safety-distance validity, SAGA effectiveness, or IJHE readiness.
All input and output paths must remain outside the repository.
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import subprocess
from statistics import median
from typing import Any

import numpy as np

from h2station.api import ProcessSettings
from h2station.operations import ProcessRuntime
from h2station.risk.runtime_backend import UnavailableHyRAMBackend
from h2station.scenario import ReferenceScenario, build_reference_scenario


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_COLUMNS = (
    "time_s",
    "station_pressure_mpa_abs",
    "boundary_temperature_degC",
    "mass_flow_g_s",
    "protocol_phase",
)
MAX_BOUNDARY_PRESSURE_MPA = 125.0
MAX_BOUNDARY_TEMPERATURE_C = 85.0
MAX_MASS_FLOW_G_S = 60.0


def _outside_repository(path: Path, *, field: str) -> Path:
    resolved = path.expanduser().resolve()
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError:
        return resolved
    raise ValueError(f"{field} must be outside the repository worktree")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _git_commit() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True,
            capture_output=True, text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unavailable"


def _finite(value: object, *, field: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be numeric") from exc
    if not math.isfinite(number):
        raise ValueError(f"{field} must be finite")
    return number


def _read_event(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = [column for column in REQUIRED_COLUMNS if column not in (reader.fieldnames or ())]
        if missing:
            raise ValueError(f"{path.name}: missing canonical channels: {', '.join(missing)}")
        rows = list(reader)
    if len(rows) < 20:
        raise ValueError(f"{path.name}: component event has fewer than 20 rows")

    times = np.asarray([
        _finite(row.get("time_s"), field=f"{path.name}: time_s row {index}")
        for index, row in enumerate(rows, start=2)
    ])
    pressure = np.asarray([
        _finite(row.get("station_pressure_mpa_abs"), field=f"{path.name}: pressure row {index}")
        for index, row in enumerate(rows, start=2)
    ])
    temperature = np.asarray([
        _finite(row.get("boundary_temperature_degC"), field=f"{path.name}: temperature row {index}")
        for index, row in enumerate(rows, start=2)
    ])
    flow = np.asarray([
        _finite(row.get("mass_flow_g_s"), field=f"{path.name}: mass_flow row {index}")
        for index, row in enumerate(rows, start=2)
    ])
    phases = [str(row.get("protocol_phase") or "").strip() for row in rows]
    if not all(phases):
        raise ValueError(f"{path.name}: protocol_phase cannot be empty")
    if abs(times[0]) > 1.0e-9 or np.any(np.diff(times) <= 0.0):
        raise ValueError(f"{path.name}: time_s must be strictly increasing from zero")
    if np.any(pressure <= 0.0):
        raise ValueError(f"{path.name}: absolute pressure must be positive")
    if np.any(flow < 0.0):
        raise ValueError(f"{path.name}: negative mass flow is outside this contract")

    dt = np.diff(times)
    integrated_mass_kg = float(np.trapezoid(flow / 1000.0, times))
    active = flow > 1.0e-9
    pressure_rise = float(pressure[-1] - pressure[0])
    active_flow = float(np.mean(flow[active])) if np.any(active) else 0.0
    return {
        "path": path,
        "sha256": _sha256(path),
        "rows": len(rows),
        "duration_s": float(times[-1]),
        "times": times,
        "pressure": pressure,
        "temperature": temperature,
        "flow": flow,
        "phases": phases,
        "summary": {
            "rows": len(rows),
            "duration_s": float(times[-1]),
            "min_pressure_mpa_abs": float(np.min(pressure)),
            "max_pressure_mpa_abs": float(np.max(pressure)),
            "max_mass_flow_g_s": float(np.max(flow)),
            "integrated_mass_kg": integrated_mass_kg,
            "pressure_rise_mpa": pressure_rise,
            "active_mean_mass_flow_g_s": active_flow,
            "median_sample_period_s": float(median(dt)) if dt.size else None,
        },
    }


def _replay_event(event: dict[str, Any]) -> dict[str, Any]:
    times = event["times"]
    pressure = event["pressure"]
    temperature = event["temperature"]
    control_period = max(0.05, min(5.0, float(event["summary"]["median_sample_period_s"] or 0.5)))
    config = ReferenceScenario(
        duration_s=float(times[-1]),
        control_period_s=control_period,
        supply_pressure_profile_pa=tuple((float(t), float(p) * 1.0e6) for t, p in zip(times, pressure)),
        supply_temperature_profile_k=tuple((float(t), float(v) + 273.15) for t, v in zip(times, temperature)),
        risk_update_period_s=float(times[-1]) + 1.0,
    )
    built = build_reference_scenario(config, UnavailableHyRAMBackend())
    built.simulator.process_runtime = ProcessRuntime(
        ProcessSettings(vehicle_1=True, vehicle_1_auto_stop=True).model_dump()
    )
    samples: list[Any] = []
    trajectory = built.simulator.simulate(
        built.initial_state, float(times[-1]), control_period,
        pace_idle=False, sample_callback=samples.append,
    )
    if len(samples) < 2:
        raise RuntimeError("runtime returned fewer than two replay samples")
    return {
        "model_sample_count": len(samples),
        "model_duration_s": float(trajectory.time_s[-1]),
        "esd_triggered": trajectory.esd_time_s is not None,
        "max_hose_pressure_mpa": float(max(sample.hose_pressure_pa for sample in samples) / 1.0e6),
        "max_model_vehicle_temperature_c": float(max(sample.vehicle_temperature_k for sample in samples) - 273.15),
        "max_model_mass_flow_g_s": float(max(sample.nozzle_mass_flow_kg_s for sample in samples) * 1000.0),
        "fueling_stop_reason": samples[-1].fueling_stop_reason,
    }


def evaluate_bundle(bundle_directory: Path, output: Path) -> dict[str, Any]:
    bundle_directory = _outside_repository(bundle_directory, field="component bundle")
    output = _outside_repository(output, field="replay output")
    receipt_path = bundle_directory / "receipt.json"
    if not receipt_path.is_file():
        raise FileNotFoundError(receipt_path)
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if receipt.get("artifact_type") != "controlled_deidentified_hrs_component_bundle_receipt":
        raise ValueError("receipt artifact_type is not a component bundle receipt")
    if receipt.get("component_bundle_ready") is not True:
        raise ValueError("receipt does not attest component_bundle_ready")
    if receipt.get("runtime_parameter_application") is not False:
        raise ValueError("component replay cannot consume a parameter-applied receipt")
    event_paths = sorted(bundle_directory.glob("component_event_*.csv"))
    if len(event_paths) != int(receipt.get("event_count") or 0) or len(event_paths) < 3:
        raise ValueError("bundle event files do not match the receipt event_count")

    events = [_read_event(path) for path in event_paths]
    event_results: list[dict[str, Any]] = []
    all_envelope_pass = True
    replay_pass = True
    for event in events:
        summary = event["summary"]
        envelope = {
            "pressure_within_model_envelope": summary["max_pressure_mpa_abs"] <= MAX_BOUNDARY_PRESSURE_MPA,
            "temperature_within_fueling_envelope": float(np.max(event["temperature"])) <= MAX_BOUNDARY_TEMPERATURE_C,
            "mass_flow_within_model_envelope": summary["max_mass_flow_g_s"] <= MAX_MASS_FLOW_G_S,
        }
        all_envelope_pass = all_envelope_pass and all(envelope.values())
        try:
            replay = _replay_event(event)
            replay_status = "EXECUTED"
        except Exception as exc:  # pragma: no cover - failure is reported in the artifact
            replay = {"error_type": type(exc).__name__, "error": str(exc)[:240]}
            replay_status = "FAILED"
            replay_pass = False
        event_results.append({
            "event_index": len(event_results) + 1,
            "normalized_file_sha256": event["sha256"],
            "observed": summary,
            "fixed_envelope": envelope,
            "replay_status": replay_status,
            "runtime_replay": replay,
        })

    decision = "COMPONENT_REPLAY_DIAGNOSTIC_PASS" if all_envelope_pass and replay_pass else "COMPONENT_REPLAY_REVIEW"
    return {
        "schema_version": 1,
        "artifact_type": "controlled_component_bundle_replay_diagnostic",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "decision": decision,
        "source_commit": _git_commit(),
        "source_identifiers_published": False,
        "raw_rows_persisted": False,
        "bundle_receipt_sha256": _sha256(receipt_path),
        "event_count": len(event_results),
        "fixed_envelope": {
            "maximum_boundary_pressure_mpa_abs": MAX_BOUNDARY_PRESSURE_MPA,
            "maximum_boundary_temperature_degC": MAX_BOUNDARY_TEMPERATURE_C,
            "maximum_mass_flow_g_s": MAX_MASS_FLOW_G_S,
        },
        "envelope_pass": all_envelope_pass,
        "runtime_replay_pass": replay_pass,
        "events": event_results,
        "predictive_validation": False,
        "runtime_parameter_application": False,
        "full_loop_holdout_eligible": False,
        "claim_boundary": (
            "This artifact is a de-identified station/dispenser component replay diagnostic. "
            "The measured pressure and temperature are exogenous boundary inputs; no model "
            "parameter is fitted and no predictive accuracy is claimed. It does not validate "
            "vehicle filling, safety-distance consequences, SAGA effectiveness, or IJHE readiness."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle-directory", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = _outside_repository(args.output, field="replay output")
    if output.exists():
        raise FileExistsError("replay output must not already exist")
    result = evaluate_bundle(args.bundle_directory, output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"decision": result["decision"], "output": str(output)}, ensure_ascii=False))
    return 0 if result["decision"] == "COMPONENT_REPLAY_DIAGNOSTIC_PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
