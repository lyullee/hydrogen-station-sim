"""Run a transparent endpoint-only screen against public CIP dispenser tables.

The source provides endpoint and initial conditions, not a synchronized raw
station-to-vehicle time series. This script therefore reports a negative or
contextual endpoint diagnostic only; it cannot close the full-loop validation gate.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from h2station.api import ProcessSettings
from h2station.operations import ProcessRuntime
from h2station.risk.runtime_backend import UnavailableHyRAMBackend
from h2station.scenario import ReferenceScenario, build_reference_scenario

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "research/cip_dispenser_endpoint_screen.json"

CASES = (
    {
        "case_id": "cip-35mpa-logistics",
        "pressure_class_mpa": 35.0,
        "duration_s": 470.0,
        "initial_pressure_mpa": 2.2,
        "initial_temperature_c": 64.0,
        "tank_volume_m3": 0.420,
        "source_pressure_mpa": 43.0,
        "source_temperature_c": 26.0,
        "reported_ramp_mpa_min": 4.45,
        "observed_final_pressure_mpa": 35.4,
        "observed_final_temperature_c": 64.0,
        "observed_mass_kg": 8.21,
        "observed_soc_percent": 88.0,
        "observed_duration_s": 470.0,
    },
    {
        "case_id": "cip-70mpa-passenger",
        "pressure_class_mpa": 70.0,
        "duration_s": 276.0,
        "initial_pressure_mpa": 1.7,
        "initial_temperature_c": 2.0,
        "tank_volume_m3": 0.1224,
        "source_pressure_mpa": 85.0,
        "source_temperature_c": -40.0,
        "reported_ramp_mpa_min": 17.4,
        "observed_final_pressure_mpa": 81.6,
        "observed_final_temperature_c": 65.8,
        "observed_mass_kg": 5.08,
        "observed_soc_percent": 99.0,
        "observed_duration_s": 276.0,
    },
)


def run_case(case: dict) -> dict:
    duration = float(case["duration_s"])
    target = float(case["observed_final_pressure_mpa"])
    cfg = ReferenceScenario(
        duration_s=duration,
        control_period_s=0.5,
        ambient_temperature_k=298.15,
        initial_vehicle_pressure_pa=float(case["initial_pressure_mpa"]) * 1e6,
        initial_vehicle_temperature_k=float(case["initial_temperature_c"]) + 273.15,
        vehicle_internal_volume_m3=float(case["tank_volume_m3"]),
        vehicle_nominal_working_pressure_pa=float(case["pressure_class_mpa"]) * 1e6,
        target_vehicle_pressure_pa=target * 1e6,
        average_pressure_ramp_rate_pa_s=float(case["reported_ramp_mpa_min"]) * 1e6 / 60.0,
        delivery_temperature_k=float(case["source_temperature_c"]) + 273.15,
        maximum_gas_temperature_k=358.15,
        supply_pressure_profile_pa=(
            (0.0, float(case["source_pressure_mpa"]) * 1e6),
            (duration, float(case["source_pressure_mpa"]) * 1e6),
        ),
        risk_update_period_s=duration + 1.0,
    )
    built = build_reference_scenario(cfg, UnavailableHyRAMBackend())
    built.simulator.process_runtime = ProcessRuntime(ProcessSettings(
        vehicle_1=True,
        vehicle_1_auto_stop=True,
        vehicle_1_target_pressure_mpa=target,
    ).model_dump())
    trajectory = built.simulator.simulate(
        built.initial_state, duration, cfg.control_period_s, pace_idle=False,
    )
    reference_density = built.station.partial_station.controller.soc_model.reference_density_kg_m3
    predicted_soc = 100.0 * trajectory.vehicle_density_kg_m3[-1] / reference_density
    predicted = {
        "final_pressure_mpa": float(trajectory.vehicle_pressure_pa[-1] / 1e6),
        "final_temperature_c": float(trajectory.vehicle_temperature_k[-1] - 273.15),
        "final_soc_percent": float(predicted_soc),
        "stop_reason": built.simulator.process_runtime.snapshot()["stop_reason"]["vehicle_1"],
        "peak_temperature_c": float(max(temperature - 273.15 for temperature in trajectory.vehicle_temperature_k)),
    }
    observed = {
        "final_pressure_mpa": case["observed_final_pressure_mpa"],
        "final_temperature_c": case["observed_final_temperature_c"],
        "soc_percent": case["observed_soc_percent"],
        "duration_s": case["observed_duration_s"],
        "mass_kg": case["observed_mass_kg"],
    }
    return {
        "case_id": case["case_id"],
        "observed": observed,
        "predicted": predicted,
        "endpoint_errors": {
            "pressure_mpa": predicted["final_pressure_mpa"] - observed["final_pressure_mpa"],
            "temperature_c": predicted["final_temperature_c"] - observed["final_temperature_c"],
            "soc_percentage_points": predicted["final_soc_percent"] - observed["soc_percent"],
        },
        "claim_boundary": "endpoint-only public-table diagnostic; no synchronized time-series or full-loop validation claim",
    }


def main() -> None:
    source = {
        "title": "Study on comprehensive evaluation of 35 MPa/70 MPa hydrogen dispenser refueling performance",
        "doi": "10.19799/j.cnki.2095-4239.2020.0049",
        "url": "https://esst.cip.com.cn/article/2020/2095-4239/2095-4239-2020-9-3-702.shtml",
        "publisher": "Energy Storage Science and Technology",
        "table_downloads": [
            {"table": "T1", "url": "https://esst.cip.com.cn/article/2020/2095-4239/2095-4239-2020-9-3-702/T1.csv.zip", "sha256": "b98ac67fcf751801a86228dd8ee8779e50c2832ba5a78ed3c187654dc7725ac3"},
            {"table": "T2", "url": "https://esst.cip.com.cn/article/2020/2095-4239/2095-4239-2020-9-3-702/T2.csv.zip", "sha256": "06beb809e4021e3aee9e641e07ac4cdef98a9ae71a2abfa2ab7009a8ae28ecd0"},
            {"table": "T4", "url": "https://esst.cip.com.cn/article/2020/2095-4239/2095-4239-2020-9-3-702/T4.csv.zip", "sha256": "44c6fc612715ef018ecde9e4a734eee86fa75640b5b91614e21b2bd035537a2e"},
        ],
        "reuse_status": "public_download; article copyright and derived-data reuse terms require citation/permission review",
    }
    results = [run_case(case) for case in CASES]
    payload = {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "completed_endpoint_only_negative_diagnostic",
        "source": source,
        "model": {
            "script": "scripts/run_cip_dispenser_endpoint_screen.py",
            "git_commit": "runtime",
            "maximum_gas_temperature_c": 85.0,
            "source_pressure_boundary": "constant published source pressure per case",
            "hyraM_backend": "unavailable_backend_for_process_screen",
        },
        "aggregate": {
            "case_count": len(results),
            "stop_reason_counts": {reason: sum(row["predicted"]["stop_reason"] == reason for row in results) for reason in sorted({row["predicted"]["stop_reason"] for row in results})},
            "claim_boundary": "This diagnostic does not close the independent station-to-vehicle full-loop gate and is not a safety-distance claim.",
        },
        "cases": results,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(payload["aggregate"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
