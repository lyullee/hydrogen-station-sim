"""FastAPI service for hydrogen-station simulation and monitoring."""

from __future__ import annotations

import asyncio
import json
import os
import re
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from dataclasses import replace, asdict
from pathlib import Path
from threading import Lock
from typing import Any, Literal
from uuid import uuid4

import numpy as np
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, ConfigDict, model_validator

from .full_station import FullStationState
from .risk.runtime_backend import load_hyram_backend
from .risk.sensor_assessment import assess_sensor_cases, available_sensor_inputs
from .risk.scenario_planning import parse_saga_plan
from .safe_operation import SafeOperationSample
from .scenario import ReferenceScenario, build_reference_scenario
from .safety_runtime import FaultEvent, FaultKind, FaultSchedule
from .tabulated import PropsSI
from .hazop.database import EventStore, load_catalog
from .hazop.mapping import coverage as hazop_coverage
from .hazop.runtime import HazopMonitor


class FaultInput(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    event_id: str
    kind: FaultKind
    target: str
    start_time_s: float = Field(ge=0.0)
    end_time_s: float | None = None
    magnitude: float = 0.0
    leak_diameter_mm: float | None = Field(default=None, gt=0.0)
    indoor: bool = False
    rate_s: float = Field(default=30.0, gt=0.0)
    external_temperature_c: float | None = Field(default=None, gt=-273.15, le=2500.0)
    heat_transfer_ua_w_k: float = Field(default=0.0, ge=0.0, le=1.0e8)

    @model_validator(mode="after")
    def validate_event(self):
        self.to_event()
        return self

    def to_event(self) -> FaultEvent:
        return FaultEvent(
            event_id=self.event_id,
            kind=self.kind,
            target=self.target,
            start_time_s=self.start_time_s,
            end_time_s=self.end_time_s,
            magnitude=self.magnitude,
            leak_diameter_m=(
                self.leak_diameter_mm / 1000.0
                if self.leak_diameter_mm is not None else None
            ),
            indoor=self.indoor,
            rate_s=self.rate_s,
            external_temperature_k=(
                self.external_temperature_c + 273.15
                if self.external_temperature_c is not None else None
            ),
            heat_transfer_ua_w_k=self.heat_transfer_ua_w_k,
        )


class SimulationInput(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    duration_s: float = Field(default=300.0, gt=0.0, le=3600.0)
    continuous: bool = False
    control_period_s: float = Field(default=0.2, gt=0.0, le=2.0)
    ambient_temperature_c: float = Field(default=25.0, ge=-40.0, le=50.0)
    initial_vehicle_pressure_mpa: float = Field(default=5.0, gt=0.0, le=70.0)
    initial_vehicle_temperature_c: float = Field(default=25.0, ge=-40.0, le=85.0)
    initial_vehicle_2_pressure_mpa: float = Field(default=8.0, gt=0.0, le=70.0)
    initial_vehicle_2_temperature_c: float = Field(default=25.0, ge=-40.0, le=85.0)
    target_vehicle_pressure_mpa: float = Field(default=70.0, gt=1.0, le=87.5)
    target_vehicle_2_pressure_mpa: float = Field(default=70.0, gt=1.0, le=87.5)
    pressure_ramp_rate_mpa_min: float = Field(default=12.0, gt=0.0, le=30.0)
    delivery_temperature_c: float = Field(default=-40.0, ge=-50.0, le=20.0)
    maximum_mass_flow_g_s: float = Field(default=60.0, gt=0.0, le=300.0)
    faults: list[FaultInput] = Field(default_factory=list)

    @model_validator(mode="after")
    def unique_fault_ids(self):
        if len({f.event_id for f in self.faults}) != len(self.faults):
            raise ValueError("Fault event IDs must be unique")
        return self


class SagaChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=1200)


class SagaAnalysisInput(BaseModel):
    question: str = Field(default="현재 공정의 이상 징후와 조치 우선순위를 분석해 주세요.", max_length=1200)
    trigger: str = Field(default="manual", pattern="^(manual|periodic|alarm)$")
    scenario_mode: bool = False
    history: list[SagaChatTurn] = Field(default_factory=list, max_length=8)


app = FastAPI(
    title="Hydrogen Station Dynamic Simulator",
    version="0.1.0",
    description="First-principles hydrogen station, protection, and HyRAM runtime",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_jobs: dict[str, dict[str, Any]] = {}
_jobs_lock = Lock()
_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="h2station")


def _analyze_frame(frame: dict[str, Any]) -> dict[str, Any]:
    """Turn live process signals into a compact operator-facing assessment."""
    pressure = max(float(frame.get("vehicle_pressure_mpa", 0.0)), float(frame.get("vehicle_2_pressure_mpa", 0.0)))
    temperature = max(float(frame.get("vehicle_temperature_c", 25.0)), float(frame.get("vehicle_2_temperature_c", 25.0)))
    leak = float(frame.get("total_leak_flow_g_s", 0.0))
    esd = bool(frame.get("esd", False))
    active_faults = list(frame.get("active_faults") or [])
    detector_values = [float(x.get("value", 0.0)) for x in (frame.get("gas_detectors") or {}).values() if isinstance(x, dict)]
    max_detector = max(detector_values, default=0.0)
    findings: list[str] = []
    score = 0
    hazop_active = (frame.get("hazop") or {}).get("active", [])
    if hazop_active:
        findings.append(f"HAZOP 임계값 초과 후보 {len(hazop_active)}건: 센서와 운전 조건 확인")
        score = 3 if any(a.get("severity") == "TRIP" for a in hazop_active) else 2
    if pressure >= 87.5:
        findings.append(f"차량 압력 {pressure:.1f} MPa: 설계 상한 근접")
        score = max(score, 3)
    elif pressure >= 82.0:
        findings.append(f"차량 압력 {pressure:.1f} MPa: 상한 감시")
        score = max(score, 2)
    if temperature >= 85.0:
        findings.append(f"차량 온도 {temperature:.1f} °C: 충전 온도 한계")
        score = max(score, 3)
    elif temperature >= 70.0:
        findings.append(f"차량 온도 {temperature:.1f} °C: 열적 여유 감소")
        score = max(score, 2)
    if leak > 0.1:
        findings.append(f"누출 {leak:.2f} g/s: 격리와 피해영향예측 확인 필요")
        score = max(score, 3)
    elif leak > 0.001:
        findings.append(f"누출 {leak:.2f} g/s: 가스검지기 추적 중")
        score = max(score, 2)
    if max_detector >= 2.0:
        findings.append(f"가스검지기 최대 {max_detector:.2f} vol% H₂: 검지기 TRIP 후보")
        score = max(score, 3)
    elif max_detector >= 1.0:
        findings.append(f"가스검지기 최대 {max_detector:.2f} vol% H₂: 경보 후보")
        score = max(score, 2)
    if active_faults:
        findings.append("사고 주입 신호가 공정 상태와 연동됨")
        score = max(score, 1)
    if esd:
        findings.insert(0, "ESD 래치: 공정 격리 상태")
        score = 3
    status = ("CRITICAL" if score >= 3 else "WARNING" if score >= 2 else "ADVISORY" if score else "NORMAL")
    headline = {"CRITICAL":"즉시 현장 확인 및 피해영향예측 확인", "WARNING":"운전 조건과 검지기 추세 감시", "ADVISORY":"사고 입력 영향 추적 중", "NORMAL":"모든 연결 신호가 정상 범위"}[status]
    return {"status": status, "score": score, "headline": headline, "findings": findings, "max_detector_volpct": max_detector}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _set_job(job_id: str, **changes: Any) -> None:
    with _jobs_lock:
        _jobs[job_id].update(changes)


def _execute_simulation(job_id: str, request: SimulationInput) -> None:
    try:
        _set_job(
            job_id,
            status="running",
            started_at=_utc_now(),
            updated_at=_utc_now(),
            progress=5,
            phase="initializing",
            activity="열물성과 피해영향예측 엔진을 초기화하는 중",
            simulated_time_s=0.0,
            duration_s=request.duration_s,
            solver_step=0,
            total_steps=int(np.ceil(request.duration_s / request.control_period_s)),
        )
        backend = load_hyram_backend()
        config = ReferenceScenario(
            duration_s=request.duration_s,
            control_period_s=request.control_period_s,
            ambient_temperature_k=request.ambient_temperature_c + 273.15,
            initial_vehicle_pressure_pa=(
                request.initial_vehicle_pressure_mpa * 1.0e6
            ),
            initial_vehicle_temperature_k=(
                request.initial_vehicle_temperature_c + 273.15
            ),
            initial_vehicle_2_pressure_pa=(
                request.initial_vehicle_2_pressure_mpa * 1.0e6
            ),
            initial_vehicle_2_temperature_k=(
                request.initial_vehicle_2_temperature_c + 273.15
            ),
            target_vehicle_pressure_pa=request.target_vehicle_pressure_mpa * 1.0e6,
            target_vehicle_2_pressure_pa=(
                request.target_vehicle_2_pressure_mpa * 1.0e6
            ),
            average_pressure_ramp_rate_pa_s=(
                request.pressure_ramp_rate_mpa_min * 1.0e6 / 60.0
            ),
            delivery_temperature_k=request.delivery_temperature_c + 273.15,
            maximum_mass_flow_kg_s=request.maximum_mass_flow_g_s / 1000.0,
            risk_update_period_s=max(1.0, 5.0 * request.control_period_s),
            fault_events=tuple(fault.to_event() for fault in request.faults),
        )
        built = build_reference_scenario(config, backend)
        def apply_runtime_commands(time_s: float) -> None:
            with _jobs_lock:
                job = _jobs[job_id]
                commands = job["pending_fault_commands"]
                if not commands:
                    return
                registry = job["fault_registry"]
                for command, payload in commands:
                    if command == "add":
                        event = payload
                        if event.start_time_s < time_s:
                            shift = time_s - event.start_time_s
                            event = replace(event, start_time_s=time_s,
                                end_time_s=(event.end_time_s + shift if event.end_time_s is not None else None))
                        registry[event.event_id] = event
                    elif command == "remove":
                        event = registry.get(payload)
                        if event is not None:
                            if time_s <= event.start_time_s:
                                del registry[payload]
                            else:
                                registry[payload] = replace(event, end_time_s=max(time_s, event.start_time_s + 1e-6))
                commands.clear()
                built.simulator.fault_injector.schedule = FaultSchedule(tuple(registry.values()))
        hazop_monitor = HazopMonitor(run_id=job_id, store=EventStore(), virtual_detectors=True)
        built.simulator.hazop_monitor = hazop_monitor
        _set_job(
            job_id,
            progress=20,
            phase="integrating",
            activity="Solving process, control, safety, and dynamic risk states",
            simulated_time_s=0.0,
            duration_s=config.duration_s,
            hyram_backend=backend.name,
            updated_at=_utc_now(),
        )

        def report_progress(simulated_time_s: float, duration_s: float) -> None:
            fraction = min(1.0, max(0.0, simulated_time_s / duration_s))
            total_steps = int(np.ceil(duration_s / request.control_period_s))
            _set_job(
                job_id,
                progress=20 + int(round(64.0 * fraction)),
                simulated_time_s=round(simulated_time_s, 3),
                solver_step=min(
                    int(round(simulated_time_s / request.control_period_s)),
                    total_steps,
                ),
                total_steps=total_steps,
                updated_at=_utc_now(),
            )

        reference_density = float(
            PropsSI("Dmass", "P", 70.0e6, "T", 288.15, "Hydrogen")
        )

        def report_sample(sample: SafeOperationSample) -> None:
            with _jobs_lock:
                frames = _jobs[job_id]["frames"]
                sequence = _jobs[job_id].get("next_sequence", 0)
                frame = {
                        "sequence": sequence,
                        "time_s": sample.time_s,
                        "vehicle_pressure_mpa": sample.vehicle_pressure_pa / 1.0e6,
                        "vehicle_temperature_c": sample.vehicle_temperature_k - 273.15,
                        "soc_percent": 100.0 * sample.vehicle_density_kg_m3 / reference_density,
                        "vehicle_2_pressure_mpa": sample.vehicle_2_pressure_pa / 1.0e6,
                        "vehicle_2_temperature_c": sample.vehicle_2_temperature_k - 273.15,
                        "vehicle_2_soc_percent": 100.0 * sample.vehicle_2_density_kg_m3 / reference_density,
                        "pcv_flow_g_s": sample.pcv_mass_flow_kg_s * 1000.0,
                        "nozzle_flow_g_s": sample.nozzle_mass_flow_kg_s * 1000.0,
                        "pcv_1_flow_g_s": sample.pcv_1_mass_flow_kg_s * 1000.0,
                        "pcv_2_flow_g_s": sample.pcv_2_mass_flow_kg_s * 1000.0,
                        "nozzle_1_flow_g_s": sample.nozzle_1_mass_flow_kg_s * 1000.0,
                        "nozzle_2_flow_g_s": sample.nozzle_2_mass_flow_kg_s * 1000.0,
                        "total_leak_flow_g_s": sample.total_leak_mass_flow_kg_s * 1000.0,
                        "hose_pressure_mpa": sample.hose_pressure_pa / 1.0e6,
                        "hose_temperature_c": sample.hose_temperature_k - 273.15,
                        "hose_2_pressure_mpa": sample.hose_2_pressure_pa / 1.0e6,
                        "hose_2_temperature_c": sample.hose_2_temperature_k - 273.15,
                        "hazop": sample.hazop,
                        "bank_pressure_mpa": {
                            name: pressure / 1.0e6
                            for name, pressure in sample.bank_pressure_pa.items()
                        },
                        "dispatch_bank": sample.dispatch_bank,
                        "dispatch_bank_2": sample.dispatch_bank_2,
                        "recharge_bank": sample.recharge_bank,
                        "esd": sample.esd_latched,
                        "trip_causes": list(sample.trip_causes),
                        "consequence_updated": sample.consequence_updated,
                        "active_faults": list(sample.active_faults),
                    }
                previous_time = _jobs[job_id].get("last_sample_time_s")
                previous_leak = _jobs[job_id].get("last_leak_kg_s", 0.0)
                released = float(_jobs[job_id].get("released_mass_kg", 0.0))
                if previous_time is not None:
                    released += 0.5 * (previous_leak + sample.total_leak_mass_flow_kg_s) * max(0.0, sample.time_s - previous_time)
                _jobs[job_id]["released_mass_kg"] = released
                _jobs[job_id]["last_sample_time_s"] = sample.time_s
                _jobs[job_id]["last_leak_kg_s"] = sample.total_leak_mass_flow_kg_s
                _jobs[job_id]["max_vehicle_temperature_c"] = max(
                    float(_jobs[job_id].get("max_vehicle_temperature_c", -273.15)),
                    sample.vehicle_temperature_k - 273.15,
                    sample.vehicle_2_temperature_k - 273.15,
                )
                frame["released_mass_kg"] = released
                frame["peak_vehicle_temperature_c"] = _jobs[job_id]["max_vehicle_temperature_c"]
                signals = (sample.hazop or {}).get("signals", {}) if sample.hazop else {}
                frame["gas_detectors"] = {
                    tag: value for tag, value in signals.items()
                    if str(tag).startswith("GD-") and isinstance(value, dict)
                }
                frame["analysis"] = _analyze_frame(frame)
                frames.append(frame)
                _jobs[job_id]["next_sequence"] = sequence + 1
                # Keep the virtual monitor bounded while allowing it to run indefinitely.
                if len(frames) > 12000:
                    del frames[:len(frames) - 12000]
                _jobs[job_id]["hazop_detail"] = hazop_monitor.latest

        def should_stop() -> bool:
            with _jobs_lock:
                return bool(_jobs[job_id].get("stop_requested"))

        trajectory = None
        if request.continuous:
            # Continuous virtual monitoring runs bounded solver windows and carries the
            # physical state forward. The window is an implementation detail; the
            # operator sees one monotonically increasing live timeline until Stop.
            current_state = built.initial_state
            offset_s = 0.0
            first_window = True
            _set_job(job_id, progress=50, phase="monitoring", activity="무제한 가상 모니터링 실행 중", duration_s=None)
            while True:
                trajectory = built.simulator.simulate(
                    current_state,
                    config.duration_s,
                    config.control_period_s,
                    progress_callback=lambda t, end: _set_job(
                        job_id,
                        progress=50,
                        simulated_time_s=round(t, 3),
                        solver_step=int(round(t / request.control_period_s)),
                        total_steps=0,
                        updated_at=_utc_now(),
                    ),
                    sample_callback=report_sample,
                    start_time_s=offset_s,
                    reset_runtime=first_window,
                    stop_callback=should_stop,
                    runtime_command_callback=apply_runtime_commands,
                )
                current_state = trajectory.final_state or current_state
                # Keep HAZOP event timestamps strictly increasing across solver windows.
                offset_s = (float(trajectory.time_s[-1]) + 1.0e-6) if len(trajectory.time_s) else offset_s + config.duration_s
                first_window = False
                with _jobs_lock:
                    stop_requested = bool(_jobs[job_id].get("stop_requested"))
                if stop_requested:
                    break
            _set_job(job_id, progress=85, phase="serializing", activity="가상 모니터링 누적 결과 변환 중", updated_at=_utc_now())
        else:
            trajectory = built.simulator.simulate(
                built.initial_state,
                config.duration_s,
                config.control_period_s,
                progress_callback=report_progress,
                sample_callback=report_sample,
                stop_callback=should_stop,
                runtime_command_callback=apply_runtime_commands,
            )
            _set_job(
                job_id,
                progress=85,
                phase="serializing",
                activity="Converting trajectory and risk results for monitoring",
                updated_at=_utc_now(),
            )
        _set_job(
            job_id,
            progress=85,
            phase="serializing",
            activity="Converting trajectory and risk results for monitoring",
            updated_at=_utc_now(),
        )
        with _jobs_lock:
            final_faults = list(_jobs[job_id]["fault_registry"].values())
        result = _serialize_result(trajectory, built.station, backend, final_faults)
        if request.continuous:
            with _jobs_lock:
                live_job = _jobs[job_id]
                cumulative_mass = float(live_job.get("released_mass_kg", 0.0))
                max_temp = float(live_job.get("max_vehicle_temperature_c", result["summary"]["maximum_vehicle_temperature_c"]))
                elapsed = float(live_job.get("simulated_time_s", result["summary"]["duration_s"]))
            result["summary"]["duration_s"] = elapsed
            result["summary"]["released_mass_kg"] = cumulative_mass
            result["summary"]["maximum_vehicle_temperature_c"] = max_temp
            result["impact"]["released_mass_kg"] = cumulative_mass
            result["impact"]["peak_vehicle_temperature_c"] = max_temp
        result["hazop"] = hazop_monitor.summary()
        with _jobs_lock:
            retained_frames = list(_jobs[job_id].get("frames") or [])
        # A stopped continuous run retains the same bounded timeline as its stream.
        if retained_frames:
            for key in result["series"]:
                if key in retained_frames[0] and key not in {"bank_pressure_mpa", "leaks"}:
                    result["series"][key] = [f[key] for f in retained_frames]
            result["series"]["bank_pressure_mpa"] = {
                name: [f["bank_pressure_mpa"][name] for f in retained_frames]
                for name in retained_frames[0]["bank_pressure_mpa"]
            }
            for key in ("analysis", "gas_detectors", "released_mass_kg", "peak_vehicle_temperature_c", "trip_causes"):
                result["series"][key] = [f.get(key) for f in retained_frames]
            result["hazop"]["frames"] = [f["hazop"] for f in retained_frames]
            releases_by_frame = [
                {r["release_id"]: r.get("mass_flow_g_s", 0.0) for r in (f.get("hazop") or {}).get("releases", [])}
                for f in retained_frames
            ]
            result["series"]["leaks"] = {
                key: [r.get(key, 0.0) for r in releases_by_frame]
                for key in {key for r in releases_by_frame for key in r}
            }
        last_frame = retained_frames[-1] if retained_frames else None
        if last_frame:
            result["analysis"] = last_frame.get("analysis")
            result["gas_detectors"] = last_frame.get("gas_detectors", {})
        _set_job(
            job_id,
            status="complete",
            progress=100,
            phase="complete",
            activity="Simulation result is ready",
            completed_at=_utc_now(),
            updated_at=_utc_now(),
            result=result,
        )
    except Exception as exc:
        _set_job(
            job_id,
            status="failed",
            phase="failed",
            activity="Simulation stopped because an error occurred",
            completed_at=_utc_now(),
            updated_at=_utc_now(),
            error=f"{type(exc).__name__}: {exc}",
        )


def _serialize_result(trajectory, station, backend, faults=()) -> dict[str, Any]:
    bank_pressures: dict[str, list[float]] = {
        bank.parameters.name: [] for bank in station.banks
    }
    hose_pressures: list[float] = []
    hose_temperatures: list[float] = []
    soc_values: list[float] = []
    hose_2_pressures: list[float] = []
    hose_2_temperatures: list[float] = []
    soc_2_values: list[float] = []
    reference_density = float(
        PropsSI("Dmass", "P", 70.0e6, "T", 288.15, "Hydrogen")
    )
    for vector in trajectory.states:
        state = FullStationState.from_vector(vector, len(station.banks))
        for bank, bank_state in zip(station.banks, state.banks):
            bank_pressures[bank.parameters.name].append(
                bank.gas_state(bank_state).pressure_pa / 1.0e6
            )
        hose = station.partial_station.hose_gas_state(state.partial_station)
        hose_pressures.append(hose.pressure_pa / 1.0e6)
        hose_temperatures.append(hose.temperature_k - 273.15)
        if state.secondary_partial_station is None:
            raise ValueError("Dual-dispenser result is missing the secondary state")
        hose_2 = station.secondary_partial_station.hose_gas_state(
            state.secondary_partial_station
        )
        hose_2_pressures.append(hose_2.pressure_pa / 1.0e6)
        hose_2_temperatures.append(hose_2.temperature_k - 273.15)
        density = float(trajectory.vehicle_density_kg_m3[len(soc_values)])
        soc_values.append(100.0 * density / reference_density)
        density_2 = float(
            trajectory.vehicle_2_density_kg_m3[len(soc_2_values)]
        )
        soc_2_values.append(100.0 * density_2 / reference_density)

    total_leak_flow = np.zeros_like(trajectory.time_s)
    leak_series = {}
    for release_id, values in trajectory.leak_mass_flow_by_release.items():
        total_leak_flow += values
        leak_series[release_id] = (values * 1000.0).tolist()
    released_mass = float(
        np.sum(
            0.5
            * (total_leak_flow[1:] + total_leak_flow[:-1])
            * np.diff(trajectory.time_s)
        )
    ) if len(trajectory.time_s) > 1 else 0.0

    events: list[dict[str, Any]] = []
    previous_esd = False
    previous_dispatch = None
    for index, (time_s, command, dispatch) in enumerate(
        zip(
            trajectory.time_s,
            trajectory.safety_commands,
            trajectory.dispatch_bank,
        )
    ):
        if command.esd_latched and not previous_esd:
            events.append(
                {
                    "time_s": float(time_s),
                    "severity": "trip",
                    "message": "ESD activated: " + ", ".join(command.trip_causes),
                }
            )
        if dispatch != previous_dispatch and dispatch is not None:
            events.append(
                {
                    "time_s": float(time_s),
                    "severity": "info",
                    "message": f"Cascade dispatch changed to {dispatch}",
                }
            )
        previous_esd = command.esd_latched
        previous_dispatch = dispatch
    risk_updates = []
    for snapshots in trajectory.risk_snapshots:
        for snapshot in snapshots:
            if snapshot.consequence_updated:
                risk_updates.append(
                    {
                        "time_s": snapshot.time_s,
                        "release_id": snapshot.release_id,
                        "mass_flow_g_s": snapshot.mass_flow_kg_s * 1000.0,
                        "released_mass_kg": snapshot.cumulative_released_mass_kg,
                        "annualized_risk": snapshot.annualized_risk,
                        "consequence": dict(snapshot.consequence),
                    }
                )

    active_fault_series = []
    for time_s in trajectory.time_s:
        active_fault_series.append([
            f"{fault.kind.value}:{fault.target}"
            for fault in faults
            if time_s >= fault.start_time_s and (fault.end_time_s is None or time_s < fault.end_time_s)
        ])

    return {
        "summary": {
            "duration_s": float(trajectory.time_s[-1]),
            "final_vehicle_pressure_mpa": float(
                trajectory.vehicle_pressure_pa[-1] / 1.0e6
            ),
            "maximum_vehicle_temperature_c": float(
                np.max(trajectory.vehicle_temperature_k) - 273.15
            ),
            "final_soc_percent": float(soc_values[-1]),
            "final_vehicle_2_pressure_mpa": float(
                trajectory.vehicle_2_pressure_pa[-1] / 1.0e6
            ),
            "maximum_vehicle_2_temperature_c": float(
                np.max(trajectory.vehicle_2_temperature_k) - 273.15
            ),
            "final_vehicle_2_soc_percent": float(soc_2_values[-1]),
            "maximum_flow_g_s": float(
                np.max(trajectory.nozzle_mass_flow_kg_s) * 1000.0
            ),
            "released_mass_kg": released_mass,
            "esd_time_s": trajectory.esd_time_s,
            "hyram_available": bool(getattr(backend, "available", False)),
            "hyram_backend": backend.name,
            "active_faults": [fault.model_dump() if hasattr(fault, "model_dump") else asdict(fault) for fault in faults],
        },
        "series": {
            "time_s": trajectory.time_s.tolist(),
            "vehicle_pressure_mpa": (
                trajectory.vehicle_pressure_pa / 1.0e6
            ).tolist(),
            "vehicle_temperature_c": (
                trajectory.vehicle_temperature_k - 273.15
            ).tolist(),
            "soc_percent": soc_values,
            "vehicle_2_pressure_mpa": (
                trajectory.vehicle_2_pressure_pa / 1.0e6
            ).tolist(),
            "vehicle_2_temperature_c": (
                trajectory.vehicle_2_temperature_k - 273.15
            ).tolist(),
            "vehicle_2_soc_percent": soc_2_values,
            "pcv_flow_g_s": (trajectory.pcv_mass_flow_kg_s * 1000.0).tolist(),
            "nozzle_flow_g_s": (
                trajectory.nozzle_mass_flow_kg_s * 1000.0
            ).tolist(),
            "pcv_1_flow_g_s": (
                trajectory.pcv_1_mass_flow_kg_s * 1000.0
            ).tolist(),
            "pcv_2_flow_g_s": (
                trajectory.pcv_2_mass_flow_kg_s * 1000.0
            ).tolist(),
            "nozzle_1_flow_g_s": (
                trajectory.nozzle_1_mass_flow_kg_s * 1000.0
            ).tolist(),
            "nozzle_2_flow_g_s": (
                trajectory.nozzle_2_mass_flow_kg_s * 1000.0
            ).tolist(),
            "total_leak_flow_g_s": (total_leak_flow * 1000.0).tolist(),
            "hose_pressure_mpa": hose_pressures,
            "hose_temperature_c": hose_temperatures,
            "hose_2_pressure_mpa": hose_2_pressures,
            "hose_2_temperature_c": hose_2_temperatures,
            "bank_pressure_mpa": bank_pressures,
            "dispatch_bank": list(trajectory.dispatch_bank),
            "dispatch_bank_2": list(trajectory.dispatch_bank_2),
            "recharge_bank": list(trajectory.recharge_bank),
            "esd": [command.esd_latched for command in trajectory.safety_commands],
            "leaks": leak_series,
            "active_faults": active_fault_series,
        },
        "events": events,
        "risk_updates": risk_updates,
        "faults": [fault.model_dump() if hasattr(fault, "model_dump") else asdict(fault) for fault in faults],
        "impact": {
            "peak_vehicle_pressure_mpa": float(np.max(trajectory.vehicle_pressure_pa) / 1.0e6),
            "peak_vehicle_2_pressure_mpa": float(np.max(trajectory.vehicle_2_pressure_pa) / 1.0e6),
            "peak_vehicle_temperature_c": float(np.max(trajectory.vehicle_temperature_k) - 273.15),
            "peak_vehicle_2_temperature_c": float(np.max(trajectory.vehicle_2_temperature_k) - 273.15),
            "minimum_vehicle_pressure_mpa": float(np.min(trajectory.vehicle_pressure_pa) / 1.0e6),
            "minimum_vehicle_2_pressure_mpa": float(np.min(trajectory.vehicle_2_pressure_pa) / 1.0e6),
            "peak_leak_flow_g_s": float(np.max(total_leak_flow) * 1000.0) if len(total_leak_flow) else 0.0,
            "released_mass_kg": released_mass,
            "esd_time_s": trajectory.esd_time_s,
            "fault_targets": sorted({fault.target for fault in faults}),
        },
    }


@app.get("/api/health")
def health() -> dict[str, Any]:
    backend = load_hyram_backend()
    try:
        catalog = load_catalog()
        hazop_status = {"status":"ready", "rule_count":len(catalog["rules"]),
                        "sensor_count":len(catalog["sensors"]), "mode":"SIMULATION_ADVISORY"}
    except Exception as exc:
        hazop_status = {"status":"unavailable", "reason":f"{type(exc).__name__}: {exc}"}
    return {
        "status": "ready",
        "thermodynamics": "CoolProp-generated H2 property table v1",
        "solver": "SciPy BDF",
        "hyram_available": bool(getattr(backend, "available", False)),
        "hyram_backend": backend.name,
        "hyram_reason": getattr(backend, "reason", None),
        "hazop": hazop_status,
    }


@app.get("/api/config/defaults")
def default_config() -> dict[str, Any]:
    return SimulationInput().model_dump()


@app.post("/api/simulations", status_code=202)
def create_simulation(request: SimulationInput) -> dict[str, Any]:
    job_id = uuid4().hex
    with _jobs_lock:
        _jobs[job_id] = {
            "id": job_id,
            "status": "queued",
            "progress": 0,
            "phase": "queued",
            "activity": "Waiting for an available simulation worker",
            "created_at": _utc_now(),
            "updated_at": _utc_now(),
            "duration_s": request.duration_s,
            "continuous": request.continuous,
            "simulated_time_s": 0.0,
            "total_steps": int(np.ceil(request.duration_s / request.control_period_s)),
            "solver_step": 0,
            "frames": [],
            "next_sequence": 0,
            "stop_requested": False,
            "pending_fault_commands": [],
            "fault_registry": {fault.event_id: fault.to_event() for fault in request.faults},
        }
    _executor.submit(_execute_simulation, job_id, request)
    return {"id": job_id, "status": "queued"}


@app.get("/api/simulations/{job_id}")
def simulation_status(job_id: str) -> dict[str, Any]:
    with _jobs_lock:
        job = _jobs.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Simulation not found")
        return {
            key: value
            for key, value in job.items()
            if key not in {"result", "frames", "hazop_detail", "pending_fault_commands", "fault_registry"}
        }


@app.get("/api/simulations/{job_id}/frames")
def simulation_frames(job_id: str, after: int = -1) -> dict[str, Any]:
    """Resume telemetry over HTTP when WebSocket transport is unavailable."""
    with _jobs_lock:
        job = _jobs.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Simulation not found")
        return {
            "job": {k: v for k, v in job.items() if k not in {"result", "frames", "hazop_detail", "pending_fault_commands", "fault_registry"}},
            "frames": [f for f in job.get("frames", []) if f["sequence"] > after],
        }


@app.get("/api/simulations/{job_id}/faults")
def list_simulation_faults(job_id: str) -> dict[str, Any]:
    with _jobs_lock:
        job = _jobs.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Simulation not found")
        time_s = float(job.get("simulated_time_s", 0.0))
        events = list(job["fault_registry"].values()) + [
            payload for command, payload in job["pending_fault_commands"] if command == "add"
        ]
        return {"time_s": time_s, "faults": [
            {"event_id": event.event_id, "kind": event.kind.value, "target": event.target,
             "start_time_s": event.start_time_s, "end_time_s": event.end_time_s,
             "active": event.active_at(time_s)}
            for event in events if event.end_time_s is None or event.end_time_s > time_s
        ]}


def _invoke_saga(prompt: str, answer_length: str = "concise") -> dict[str, Any]:
    saga_url = os.getenv("H2STATION_SAGA_URL", "http://127.0.0.1:8090").rstrip("/") + "/api/chat"
    body = json.dumps({"message": prompt[:9900], "mode": "chat", "answer_length": answer_length},
                      ensure_ascii=False).encode("utf-8")
    with urlopen(Request(saga_url, data=body, headers={"Content-Type": "application/json"}), timeout=35) as response:
        return json.load(response)


def _safe_saga_text(answer: str) -> str:
    """Remove generic calculation requests and claims of a certified radius."""
    unsafe_radius = re.compile(r"(?:안전\s*반경|영향\s*반경).{0,50}(?:확정|보장|안전)|(?:확정|안전).{0,30}(?:안전\s*반경|영향\s*반경)")
    def allowed(line: str) -> bool:
        compact = re.sub(r"[\s`'\"‘’“”·]", "", line).lower()
        deferred_calculation = (any(term in compact for term in ("피해영향", "hyram", "영향범위"))
            and (bool(re.search(r"(?:계산|평가)(?:이|을|를)?(?:필요|요청|권장|해보|하시|실행)", compact))
                 or ("필요시" in compact and "계산" in compact and "요청" in compact)))
        return not deferred_calculation and not unsafe_radius.search(line)
    return "\n".join(line for line in answer.splitlines() if allowed(line)).strip()


def _mentioned_hazop_nodes(question: str, catalog: dict[str, Any]) -> list[dict[str, Any]]:
    normalized = re.sub(r"\s+", "", question).lower()
    matched = [node for node in catalog["nodes"]
               if str(node["node_id"]).lower() in normalized
               or (node.get("설비_라인") and re.sub(r"\s+", "", str(node["설비_라인"])).lower() in normalized)]
    aliases: list[str] = []
    if any(term in normalized for term in ("디스펜서", "충전기", "충전호스")):
        first = any(term in normalized for term in ("디스펜서1", "1번디스펜서", "충전기1", "1번충전기", "1번호스"))
        second = any(term in normalized for term in ("디스펜서2", "2번디스펜서", "충전기2", "2번충전기", "2번호스"))
        aliases.extend(["N13"] if first and not second else ["N17"] if second and not first else ["N13", "N17"])
    if "저장" in normalized:
        banks = {"고압": "N09", "중압": "N08", "저압": "N07"}
        requested = [node_id for word, node_id in banks.items() if word in normalized]
        aliases.extend(requested or ["N07", "N08", "N09"])
    for node in catalog["nodes"]:
        if node["node_id"] in aliases and node not in matched:
            matched.append(node)
    return matched


def _scenario_requested(request: SagaAnalysisInput) -> bool:
    if request.scenario_mode:
        return True
    question = re.sub(r"\s+", "", request.question)
    if request.trigger != "manual":
        return False
    if "시나리오" in question and any(word in question for word in ("생성", "만들", "평가", "계산", "비교", "제안")):
        return True
    hypothetical_leak = "누출" in question and any(word in question for word in ("발생했을때", "발생하면", "발생할경우", "가정", "예상", "만약"))
    impact_request = any(word in question for word in ("피해", "영향", "범위", "계산", "평가"))
    return hypothetical_leak and impact_request


def _scenario_result_summary(results: list[dict[str, Any]]) -> str:
    lines = ["**SAGA 제안 시나리오 · 현재 센서 기준 피해영향예측**"]
    for row in results:
        label = f"{row.get('scenario_id', '?')} · {row['node_id']} · {row.get('orifice_diameter_mm', 0):g} mm 가정 누출"
        if row.get("calculation_status") != "calculated":
            lines.append(f"- {label}: 계산 결과 없음 ({row.get('calculation_status')}; {row.get('reason', '입력 확인 필요')}).")
            continue
        extent = row.get("sampled_effect_radius_m")
        sample_max = float(row.get("sampled_max_distance_m") or 0)
        range_text = (f"{float(extent):g} m 관측점까지 임계값 초과" if extent
            else f"{sample_max:g} m까지 표본 관측점에서 임계값 미달")
        source_label = ("대체 신호" if row.get("sensor_basis") == "PROXY" else "목표 설비 직접 신호")
        lines.append(
            f"- {label}: {source_label} · {row['pressure_sensor']}({row.get('pressure_source_node_id', row['node_id'])}) "
            f"{row['current_pressure_mpa']:.2f} MPa, "
            f"{row['temperature_sensor']}({row.get('temperature_source_node_id', row['node_id'])}) "
            f"{row['current_temperature_c']:.1f} °C → "
            f"누출유량 {float(row.get('mass_flow_g_s') or 0):.2f} g/s, "
            f"열복사 최대 {float(row.get('maximum_heat_flux_w_m2') or 0):.0f} W/m², "
            f"과압 최대 {float(row.get('maximum_overpressure_pa') or 0):.0f} Pa; {range_text}.")
    lines.append("이 결과는 가상 누출의 표본 관측점 계산이며 실제 사고 발생이나 현장 안전반경을 뜻하지 않습니다.")
    return "\n".join(lines)


async def _run_saga_scenario_analysis(
    frame: dict[str, Any], catalog: dict[str, Any], backend: Any,
    request: SagaAnalysisInput, active: list[dict[str, Any]],
    mentioned_ids: set[str], sensor_count: int,
) -> dict[str, Any]:
    source_inputs = available_sensor_inputs(frame, catalog)
    if not source_inputs["pressure"] or not source_inputs["temperature"]:
        return {"time_s": frame.get("time_s"), "trigger": request.trigger,
                "scenario_mode": True, "answer": "현재 사용할 수 있는 압력 또는 온도 센서값이 전혀 없어 수치 계산을 수행하지 않았습니다.",
                "model": "", "proposed_scenarios": [], "impact_results": [], "sensor_count": sensor_count}
    target_ids = mentioned_ids or {case["node_id"] for case in catalog["cases"]}
    def source_distance(row: dict[str, Any]) -> int:
        return min(abs(int(row["node_id"][1:]) - int(target[1:])) for target in target_ids)
    source_inputs["pressure"].sort(key=source_distance)
    source_inputs["temperature"].sort(key=source_distance)
    target_nodes = [{"node_id": case["node_id"], "case_id": case["case_id"],
                     "name": next((node.get("설비_라인") for node in catalog["nodes"]
                                   if node["node_id"] == case["node_id"]), None),
                     "expected_pressure": case.get("압력_sensor"),
                     "expected_temperature": case.get("온도_sensor")}
                    for case in catalog["cases"] if case["node_id"] in target_ids]
    eligible_ids = {row["node_id"] for row in target_nodes}
    pressure_tags = {row["sensor_id"] for row in source_inputs["pressure"]}
    temperature_tags = {row["sensor_id"] for row in source_inputs["temperature"]}
    sizes = [{"leak_size_id": row["size_id"], "diameter_mm": row["직경_mm"]}
             for row in catalog["leak_sizes"] if isinstance(row.get("직경_mm"), (int, float))
             and 0.1 <= row["직경_mm"] <= 3.0]
    rule_ids = {row.get("rule_id") for row in active if isinstance(row, dict)}
    relevant_nodes = mentioned_ids | {row.get("node_id") for row in active if isinstance(row, dict)}
    if not relevant_nodes:
        relevant_nodes = {"N09", "N13", "N17"}
    rules = [{"rule_id": row["rule_id"], "node_id": row["node_id"],
              "sensor_id": row["sensor_id"], "name": row["시나리오명"],
              "operator": row["연산자"], "threshold": row["임계값"],
              "unit": row["단위"], "severity": row["등급"]}
             for row in catalog["rules"] if row["rule_id"] in rule_ids or row["node_id"] in relevant_nodes][:24]
    plan_context = {"question": request.question, "time_s": frame.get("time_s"),
                    "target_nodes": target_nodes, "available_sensor_inputs": source_inputs,
                    "allowed_leak_sizes": sizes,
                    "active_hazop": active[:15], "hazop_rules": rules}
    example_node = target_nodes[0]["node_id"]
    example_pressure = next((row["sensor_id"] for row in source_inputs["pressure"]
                             if row["node_id"] == example_node), source_inputs["pressure"][0]["sensor_id"])
    example_temperature = next((row["sensor_id"] for row in source_inputs["temperature"]
                                if row["node_id"] == example_node), source_inputs["temperature"][0]["sensor_id"])
    example = {"scenarios": [{"node_id": example_node, "leak_size_id": "L03",
                              "pressure_sensor": example_pressure, "temperature_sensor": example_temperature,
                              "rationale": "HAZOP 근거와 선택 신호 이유"}]}
    plan_prompt = (
        "당신은 H70 수소충전소 시뮬레이션의 가상 사고 시나리오 제안자입니다. "
        "현재 센서와 HAZOP를 근거로 의미 있는 누출 시나리오 1~3개를 스스로 선택하세요. "
        "오직 JSON 객체 하나만 출력하세요. 유효한 형식 예시(그대로 복사하지 말고 직접 판단): "
        + json.dumps(example, ensure_ascii=False) + ". "
        "node_id는 target_nodes, leak_size_id는 allowed_leak_sizes 중에서만 선택하세요. "
        "pressure_sensor와 temperature_sensor는 available_sensor_inputs의 현재 GOOD 태그 중 직접 선택하세요. "
        "목표 설비 직접 센서를 우선 사용하고 없으면 물리적으로 가장 가까운 공정 신호를 대체값으로 고르세요. "
        "목표와 출처가 다르면 rationale에 대체 이유를 명시하세요. 압력·온도 수치를 만들지 마세요. "
        "시나리오별 노드·구경 조합은 중복하지 마세요. "
        "제안은 사고 주입이나 설비 제어가 아닌 계산용 가정입니다. 설명문이나 Markdown 코드를 붙이지 마세요.\n"
        + json.dumps(plan_context, ensure_ascii=False, default=str)[:7800])
    try:
        plan_reply = await asyncio.to_thread(_invoke_saga, plan_prompt)
        try:
            proposals = parse_saga_plan(str(plan_reply.get("answer") or ""), eligible_ids, catalog,
                                        pressure_tags, temperature_tags)
        except ValueError as exc:
            retry_prompt = plan_prompt[:7300] + (f"\n이전 출력은 검증 실패({exc})였습니다. 다시 JSON 객체만 출력하세요.\n"
                + str(plan_reply.get("answer") or "")[:450])
            plan_reply = await asyncio.to_thread(_invoke_saga, retry_prompt)
            proposals = parse_saga_plan(str(plan_reply.get("answer") or ""), eligible_ids, catalog,
                                        pressure_tags, temperature_tags)
    except (URLError, HTTPError, TimeoutError, OSError) as exc:
        raise HTTPException(status_code=503, detail=f"SAGA 시나리오 제안 실패: {exc}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=f"SAGA 시나리오 형식 검증 실패: {exc}") from exc
    results = await asyncio.to_thread(assess_sensor_cases, frame, catalog, backend, [], proposals=proposals)
    interpretation_context = {"time_s": frame.get("time_s"), "question": request.question,
                              "proposed_scenarios": proposals, "impact_results": results,
                              "active_hazop": active[:15], "hazop_rules": rules,
                              "scenario_is_hypothetical": True, "process_fault_injected": False}
    interpretation_prompt = (
        "당신이 제안한 가상 누출 시나리오를 서버가 현재 GOOD 품질 센서값으로 피해영향예측 계산했습니다. "
        "아래 실제 계산 결과만 해석하세요. 계산을 다시 권하지 마세요. 사고가 실제 발생했다고 말하지 마세요. "
        "각 시나리오의 HAZOP 근거와 선택 이유, 센서값, 계산 상태, 열복사·과압, 표본 거리의 차이를 설명하세요. "
        "sensor_basis=PROXY이면 대체 센서의 태그와 원래 노드를 밝히고 목표 설비의 직접 계측값으로 표현하지 마세요. "
        "대체 신호로 계산된 경우 누락 입력을 나열하거나 추가 입력을 요구하지 말고 실제 사용한 태그·출처·가정만 밝히세요. "
        "sampled_effect_radius_m은 임계값을 초과한 최원거리 관측점일 뿐, 안전반경이나 최대 사고범위가 아닙니다. "
        "null이면 범위가 미확정입니다. 계산에 실패했으면 이유를 밝히고 수치를 만들지 마세요. "
        "사용자에게는 엔진 제품명 대신 '피해영향예측'이라고 쓰세요. 한국어 Markdown으로 간결하게 답하세요.\n"
        + json.dumps(interpretation_context, ensure_ascii=False, default=str)[:8200])
    try:
        interpretation = await asyncio.to_thread(_invoke_saga, interpretation_prompt, "standard")
    except (URLError, HTTPError, TimeoutError, OSError) as exc:
        raise HTTPException(status_code=503, detail=f"SAGA 계산 결과 해석 실패: {exc}") from exc
    narrative = _safe_saga_text(str(interpretation.get("answer") or ""))
    return {"time_s": frame.get("time_s"), "trigger": request.trigger,
            "scenario_mode": True, "answer": _scenario_result_summary(results) + ("\n\n" + narrative if narrative else ""),
            "model": interpretation.get("model", ""), "proposed_scenarios": proposals,
            "impact_results": results, "active_rule_ids": sorted(rule_ids - {None}),
            "sensor_count": sensor_count}


@app.post("/api/simulations/{job_id}/saga-analysis")
async def saga_analysis(job_id: str, request: SagaAnalysisInput) -> dict[str, Any]:
    with _jobs_lock:
        job = _jobs.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Simulation not found")
        if not job["frames"]:
            raise HTTPException(status_code=409, detail="No sensor frame available yet")
        frame = dict(job["frames"][-1])
    hazop = frame.get("hazop") or {}
    active = hazop.get("active") or []
    ids = {str(row.get("rule_id")) for row in active if isinstance(row, dict)}
    catalog = load_catalog()
    matched_rules = [rule for rule in catalog["rules"] if rule["rule_id"] in ids]
    mentioned_nodes = _mentioned_hazop_nodes(request.question, catalog)
    mentioned_ids = {node["node_id"] for node in mentioned_nodes}
    reference_rules = [rule for rule in catalog["rules"] if rule["node_id"] in mentioned_ids]
    signal_prefixes = tuple(prefix for word, prefix in (("압력", "PT-"), ("온도", "TT-"), ("유량", "FT-"), ("가스", "GD-"))
        if word in request.question)
    if signal_prefixes:
        filtered_rules = [rule for rule in reference_rules if str(rule["sensor_id"]).startswith(signal_prefixes)]
        if filtered_rules:
            reference_rules = filtered_rules
    reference_rules = reference_rules[:18]
    rule_fields = ("rule_id", "node_id", "sensor_id", "시나리오명", "연산자", "임계값", "단위", "등급", "원인후보", "사고_전개조건", "권고대응", "HyRAM_case_id")
    reference_rules = [{field: rule.get(field) for field in rule_fields} for rule in reference_rules]
    signals = hazop.get("signals") or {}
    sensor_values = {tag: {"value": value.get("value"), "unit": value.get("unit"),
        "quality": value.get("quality")} for tag, value in signals.items()
        if isinstance(value, dict) and (value.get("quality") == "GOOD" or tag.startswith("GD-"))}
    reference_tags = {rule["sensor_id"] for rule in reference_rules}
    releases = hazop.get("releases") or []
    backend = await asyncio.to_thread(load_hyram_backend)
    if _scenario_requested(request):
        return await _run_saga_scenario_analysis(frame, catalog, backend, request, active,
                                                 mentioned_ids, len(sensor_values))
    active_nodes = [str(row.get("node_id")) for row in active if isinstance(row, dict) and row.get("node_id")]
    release_nodes = [node["node_id"] for release in releases if isinstance(release, dict)
        for node in catalog["nodes"] if node.get("누출_target") == release.get("component_id")]
    candidates = [node["node_id"] for node in mentioned_nodes] + active_nodes + release_nodes
    if not candidates:
        candidates = ["N09", "N13", "N17"]
    sensor_impacts = await asyncio.to_thread(assess_sensor_cases, frame, catalog, backend, candidates)
    legacy_impacts = [{"release_id": release.get("release_id"),
        "component_id": release.get("component_id"),
        "mass_flow_g_s": release.get("mass_flow_g_s"),
        "calculation_status": (release.get("consequence") or {}).get("status"),
        "maximum_heat_flux_w_m2": (release.get("consequence") or {}).get("maximum_heat_flux_w_m2"),
        "maximum_overpressure_pa": (release.get("consequence") or {}).get("maximum_overpressure_pa"),
        "sampled_effect_radius_m": ((release.get("consequence") or {}).get("sampled_effect_radius_m") or None),
        "sampled_max_distance_m": (release.get("consequence") or {}).get("sampled_max_distance_m"),
        "effect_range_status": (release.get("consequence") or {}).get("effect_range_status"),
        "range_interpretation": ("표본 관측점에서 5 kW/m² 및 5 kPa 기준 미달; 영향 반경 미확정"
            if (release.get("consequence") or {}).get("effect_range_status") == "BELOW_THRESHOLDS_AT_SAMPLES"
            else "관측점의 임계값 초과 거리만 확인; 현장 안전반경 아님")}
        for release in releases[:5] if isinstance(release, dict)]
    assessed_releases = {row.get("release_id") for row in sensor_impacts if row.get("calculation_status") == "calculated"}
    impact_results = sensor_impacts + [row for row in legacy_impacts if row.get("release_id") not in assessed_releases]
    context = {"station":"H70 reference simulation", "time_s":frame.get("time_s"),
        "impact_results":impact_results,
        "analysis":frame.get("analysis"), "active_faults":frame.get("active_faults"),
        "hazop_active":active, "hazop_rules":matched_rules,
        "hazop_reference_rules":reference_rules,
        "reference_sensor_values":{tag: value for tag, value in sensor_values.items() if tag in reference_tags},
        "sensor_values":sensor_values,
        "hazop_nodes":[{"node_id": node["node_id"], "name": node.get("설비_라인")} for node in catalog["nodes"]],
        "impact_backend_available":bool(getattr(backend,"available",False))}
    history = "\n".join(f"{turn.role}: {turn.content}" for turn in request.history)[-1800:]
    prompt = ("당신은 H70 수소충전소 운전 분석 보조자입니다. 아래 데이터는 실제 현장 계측이 아닌 시뮬레이터 신호입니다. "
        "HAZOP 센서 임계값과 현재 신호 품질, 물리 누출 및 피해영향예측 계산 상태를 구분하세요. "
        "impact_results는 이 LLM 호출 직전에 현재 GOOD 품질 압력·온도 센서로 피해영향예측 엔진을 실행한 결과를 우선 포함합니다. "
        "calculation_basis=SENSOR_BASED_HYPOTHESIS는 실제 누출이 아닌 1 mm 가정 시나리오이며, ACTIVE_RELEASE_CURRENT_SENSORS는 현재 물리 누출입니다. 둘을 혼동하지 마세요. "
        "calculation_status=calculated이면 이미 계산된 값입니다. 피해영향 계산이나 엔진 실행을 사용자에게 권하거나 요청하지 마세요. "
        "calculation_status가 다른 경우에도 재계산을 권하지 말고 reason과 입력 상태만 사실대로 설명하세요. "
        "sampled_effect_radius_m이 null이면 표본 관측점에서 기준 미달입니다. 이때 숫자 반경을 만들지 말고 '표본 관측점에서 기준 미달, 영향 반경 미확정'이라고 쓰세요. "
        "계산 결과가 없으면 사고 범위를 추정값처럼 제시하지 마세요. 제공된 HAZOP 규칙에 없는 규칙 ID나 임계값을 만들지 마세요. "
        "사용자에게는 계산기 제품명 대신 '피해영향예측'이라고 표기하세요. "
        "관련 규칙이 전달되지 않았으면 해당 설비를 물어보세요. 규칙 목록이나 표를 요청받으면 hazop_reference_rules의 실제 rule_id와 임계값을 Markdown 표로 제시하세요. "
        "현재 경보 여부와 등록 규칙 자체를 구분하세요. 근거 태그와 실제 규칙 ID를 밝히고 한국어로 간결하게 답하세요.\n"
        f"요청 유형: {request.trigger}\n이전 대화(현재 센서보다 우선하지 않음):\n{history}\n"
        f"운전자 질문: {request.question}\n현재 데이터 및 HAZOP DB 발췌:\n"
        + json.dumps(context, ensure_ascii=False, default=str)[:7500])[:9900]
    try:
        reply = await asyncio.to_thread(_invoke_saga, prompt)
    except (URLError, HTTPError, TimeoutError, OSError) as exc:
        raise HTTPException(status_code=503, detail=f"SAGA 연결/분석 실패: {exc}") from exc
    answer = str(reply.get("answer") or "")
    answer = _safe_saga_text(answer)
    calculated = [row for row in sensor_impacts if row.get("calculation_status") == "calculated"]
    if calculated and (request.trigger != "manual" or any(term in request.question for term in ("피해", "영향", "위험", "사고", "누출"))):
        impact_lines = ["**현재 센서 기준 피해영향예측 · 표본 계산**"]
        for row in calculated[:3 if request.trigger == "alarm" else 1]:
            actual = row["calculation_basis"] == "ACTIVE_RELEASE_CURRENT_SENSORS"
            basis = "활성 누출" if actual else f"{row['orifice_diameter_mm']:g} mm 가정 누출(실제 누출 아님)"
            extent = row.get("sampled_effect_radius_m")
            sample_max = row.get("sampled_max_distance_m")
            range_text = (f"{float(extent):g} m 관측점까지 임계값 초과" if extent
                else f"{float(sample_max or 0):g} m까지 표본 관측점에서 임계값 미달")
            impact_lines.append(
                f"- {row['node_id']} · {row['pressure_sensor']} {row['current_pressure_mpa']:.2f} MPa · "
                f"{row['temperature_sensor']} {row['current_temperature_c']:.1f} °C · {basis}: "
                f"열복사 최대 {float(row.get('maximum_heat_flux_w_m2') or 0):.0f} W/m², "
                f"과압 최대 {float(row.get('maximum_overpressure_pa') or 0):.0f} Pa; {range_text}. "
                "관측점 결과이며 현장 안전반경은 확정할 수 없습니다.")
        answer = "\n".join(impact_lines) + ("\n\n" + answer if answer else "")
    if not answer:
        calculated = [row for row in impact_results if row.get("calculation_status") == "calculated"]
        answer = ("현재 센서 기준 피해영향예측 결과가 있습니다. "
            + ", ".join(f"{row.get('node_id') or row.get('component_id')}: {float(row.get('mass_flow_g_s') or 0):.2f} g/s"
                for row in calculated[:3])) if calculated else "현재 센서와 계산 상태를 확인했습니다. 피해영향 결과는 제공되지 않았습니다."
    return {"time_s":frame.get("time_s"), "trigger":request.trigger,
        "answer":answer, "model":reply.get("model", ""),
        "active_rule_ids":sorted(ids), "sensor_count":len(sensor_values),
        "impact_results":impact_results}


@app.post("/api/simulations/{job_id}/faults", status_code=202)
def add_simulation_fault(job_id: str, fault: FaultInput) -> dict[str, Any]:
    event = fault.to_event()
    with _jobs_lock:
        job = _jobs.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Simulation not found")
        if job["status"] not in {"queued", "running"} or job.get("stop_requested"):
            raise HTTPException(status_code=409, detail="Simulation is not running")
        if event.event_id in job["fault_registry"] or any(
            command == "add" and payload.event_id == event.event_id
            for command, payload in job["pending_fault_commands"]
        ):
            raise HTTPException(status_code=409, detail="Fault event ID already exists")
        job["pending_fault_commands"].append(("add", event))
        job["updated_at"] = _utc_now()
        return {"event_id": event.event_id, "status": "queued", "simulated_time_s": job["simulated_time_s"]}


@app.delete("/api/simulations/{job_id}/faults/{event_id}", status_code=202)
def remove_simulation_fault(job_id: str, event_id: str) -> dict[str, Any]:
    with _jobs_lock:
        job = _jobs.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Simulation not found")
        if job["status"] not in {"queued", "running"}:
            raise HTTPException(status_code=409, detail="Simulation is not running")
        exists = event_id in job["fault_registry"] or any(
            command == "add" and payload.event_id == event_id
            for command, payload in job["pending_fault_commands"]
        )
        if not exists:
            raise HTTPException(status_code=404, detail="Fault not found")
        job["pending_fault_commands"].append(("remove", event_id))
        job["updated_at"] = _utc_now()
        return {"event_id": event_id, "status": "removing"}


@app.post("/api/simulations/{job_id}/stop")
def stop_simulation(job_id: str) -> dict[str, Any]:
    with _jobs_lock:
        job = _jobs.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Simulation not found")
        if job.get("status") in {"complete", "failed"}:
            return {"id": job_id, "status": job.get("status")}
        job["stop_requested"] = True
        job["activity"] = "정지 요청을 반영하는 중"
        job["updated_at"] = _utc_now()
        return {"id": job_id, "status": "stopping"}


@app.get("/api/simulations/{job_id}/result")
def simulation_result(job_id: str) -> dict[str, Any]:
    with _jobs_lock:
        job = _jobs.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Simulation not found")
        if job["status"] != "complete":
            raise HTTPException(status_code=409, detail=job["status"])
        return job["result"]


@app.websocket("/api/simulations/{job_id}/stream")
async def simulation_stream(websocket: WebSocket, job_id: str) -> None:
    await websocket.accept()
    cursor = -1
    last_status_signature: tuple[Any, ...] | None = None
    try:
        while True:
            with _jobs_lock:
                job = _jobs.get(job_id)
                if job is None:
                    await websocket.send_json(
                        {"type": "error", "message": "Simulation not found"}
                    )
                    await websocket.close(code=4404)
                    return
                stored_frames = list(job.get("frames", []))
                frames = [frame for frame in stored_frames if frame.get("sequence", -1) > cursor]
                status = {
                    key: value
                    for key, value in job.items()
                    if key not in {"result", "frames", "hazop_detail", "pending_fault_commands", "fault_registry"}
                }

            signature = (
                status.get("status"),
                status.get("progress"),
                status.get("phase"),
                status.get("simulated_time_s"),
                status.get("updated_at"),
            )
            if signature != last_status_signature:
                await websocket.send_json({"type": "status", "job": status})
                last_status_signature = signature

            for frame in frames:
                await websocket.send_json({"type": "frame", "frame": frame})
                cursor = max(cursor, int(frame.get("sequence", cursor)))

            if status["status"] == "failed":
                await websocket.send_json(
                    {"type": "error", "message": status.get("error", "Simulation failed")}
                )
                await websocket.close(code=1011)
                return
            if status["status"] == "complete":
                await websocket.send_json({"type": "complete", "job": status})
                await websocket.close(code=1000)
                return
            await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        return


@app.get("/api/hazop/catalog")
def hazop_catalog() -> dict[str, Any]:
    try:
        return load_catalog()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"HAZOP catalogue unavailable: {exc}") from exc


@app.get("/api/hazop/mapping")
def hazop_mapping() -> dict[str, Any]:
    return hazop_coverage(hazop_catalog())


@app.get("/api/simulations/{job_id}/hazop")
def simulation_hazop(job_id: str) -> dict[str, Any]:
    with _jobs_lock:
        if job_id not in _jobs: raise HTTPException(status_code=404, detail="Simulation not found")
        return _jobs[job_id].get("hazop_detail") or {"state":"PENDING"}


@app.get("/api/hazop/runs/{run_id}/events")
def hazop_events(run_id: str) -> dict[str, Any]:
    return {"run_id":run_id, "events":EventStore().events(run_id)}


_web_directory = Path(__file__).resolve().parents[2] / "web"
app.mount("/", StaticFiles(directory=_web_directory, html=True), name="monitor")
