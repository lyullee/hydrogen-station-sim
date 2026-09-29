"""FastAPI service for hydrogen-station simulation and monitoring."""

from __future__ import annotations

import asyncio
from contextvars import ContextVar
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
from typing import Any, Awaitable, Callable, Literal
from uuid import uuid4

import numpy as np
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, ConfigDict, model_validator

from .full_station import FullStationState
from .operations import ProcessRuntime, RELIEF_TARGETS
from .risk.runtime_backend import load_hyram_backend
from .risk.sensor_assessment import assess_sensor_cases, available_sensor_inputs
from .risk.scenario_planning import parse_saga_plan
from .safe_operation import SafeOperationSample
from .simulation_clock import SimulationClock
from .scenario import ReferenceScenario, build_reference_scenario
from .safety_runtime import FaultEvent, FaultKind, FaultSchedule
from .tabulated import PropsSI
from .hazop.database import EventStore, load_catalog
from .hazop.mapping import coverage as hazop_coverage
from .hazop.runtime import HazopMonitor
from .hazop.response import (classify_rule, load_playbooks, response_selection,
                             prompt_guidance, render_guidance, structured_guidance)


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


class ReliefValveInput(BaseModel):
    enabled: bool = True
    open_mpa: float = Field(gt=0.1, le=120.0)
    close_mpa: float = Field(gt=0.1, le=120.0)
    orifice_mm: float = Field(default=1.0, gt=0.0, le=20.0)

    @model_validator(mode="after")
    def valid_hysteresis(self):
        if self.close_mpa >= self.open_mpa:
            raise ValueError("Relief closing pressure must be below opening pressure")
        return self


def _default_relief_valves() -> dict[str, ReliefValveInput]:
    pressures = {"low": (50.0, 49.0), "medium": (70.0, 69.0), "high": (100.0, 99.0),
                 "hose_1": (90.0, 88.0), "hose_2": (90.0, 88.0),
                 "vehicle_1": (87.5, 85.0), "vehicle_2": (87.5, 85.0)}
    return {key: ReliefValveInput(open_mpa=opening, close_mpa=closing)
            for key, (opening, closing) in pressures.items()}


class ProcessSettings(BaseModel):
    """Operator-mode requests. All process paths start isolated."""
    trailer_supply: bool = False
    pressure_recharge: bool = False
    vehicle_1: bool = False
    vehicle_2: bool = False
    trailer_pressure_mpa: float = Field(default=20.0, gt=2.0, le=50.0)
    trailer_temperature_c: float = Field(default=25.0, ge=-40.0, le=85.0)
    trailer_capacity_kg: float = Field(default=50.0, gt=0.1, le=10000.0)
    recharge_auto_stop: bool = True
    recharge_target_low_mpa: float = Field(default=46.0, gt=1.0, le=110.0)
    recharge_target_medium_mpa: float = Field(default=66.0, gt=1.0, le=110.0)
    recharge_target_high_mpa: float = Field(default=96.0, gt=1.0, le=110.0)
    vehicle_1_auto_stop: bool = True
    vehicle_1_target_pressure_mpa: float = Field(default=70.0, gt=1.0, le=110.0)
    vehicle_2_auto_stop: bool = True
    vehicle_2_target_pressure_mpa: float = Field(default=70.0, gt=1.0, le=110.0)
    relief_valves: dict[str, ReliefValveInput] = Field(default_factory=_default_relief_valves)

    @model_validator(mode="after")
    def valid_relief_targets(self):
        if set(self.relief_valves) != set(RELIEF_TARGETS):
            raise ValueError("Settings are required for every relief valve")
        return self


class SimulationInput(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    duration_s: float = Field(default=300.0, gt=0.0, le=3600.0)
    continuous: bool = False
    speed_multiplier: Literal[0.5, 1, 2, 3, 5, 10, 30, 50, 100] = 1
    control_period_s: float = Field(default=0.2, gt=0.0, le=2.0)
    ambient_temperature_c: float = Field(default=25.0, ge=-40.0, le=50.0)
    initial_vehicle_pressure_mpa: float = Field(default=5.0, gt=0.0, le=70.0)
    initial_vehicle_temperature_c: float = Field(default=25.0, ge=-40.0, le=85.0)
    initial_vehicle_2_pressure_mpa: float = Field(default=8.0, gt=0.0, le=70.0)
    initial_vehicle_2_temperature_c: float = Field(default=25.0, ge=-40.0, le=85.0)
    initial_bank_low_fill_percent: float = Field(default=90.0, ge=1.0, le=100.0)
    initial_bank_medium_fill_percent: float = Field(default=100.0 * 65.0 / 70.0, ge=1.0, le=100.0)
    initial_bank_high_fill_percent: float = Field(default=90.0, ge=1.0, le=100.0)
    target_vehicle_pressure_mpa: float = Field(default=70.0, gt=1.0, le=87.5)
    target_vehicle_2_pressure_mpa: float = Field(default=70.0, gt=1.0, le=87.5)
    pressure_ramp_rate_mpa_min: float = Field(default=12.0, gt=0.0, le=30.0)
    delivery_temperature_c: float = Field(default=-40.0, ge=-50.0, le=20.0)
    maximum_mass_flow_g_s: float = Field(default=60.0, gt=0.0, le=300.0)
    process_settings: ProcessSettings | None = None
    faults: list[FaultInput] = Field(default_factory=list)

    @model_validator(mode="after")
    def unique_fault_ids(self):
        if len({f.event_id for f in self.faults}) != len(self.faults):
            raise ValueError("Fault event IDs must be unique")
        return self


class SagaChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=1200)


class SimulationSpeedInput(BaseModel):
    speed_multiplier: Literal[0.5, 1, 2, 3, 5, 10, 30, 50, 100]


class SagaAnalysisInput(BaseModel):
    provider: Literal["service_hub", "groq"] = "service_hub"
    question: str = Field(default="현재 공정의 이상 징후와 조치 우선순위를 분석해 주세요.", max_length=1200)
    trigger: str = Field(default="manual", pattern="^(manual|periodic|alarm)$")
    scenario_mode: bool = False
    # The live monitor uses SAGA's deterministic endpoint. Only an explicitly
    # requested scenario-generation run uses the generative chat path.
    direct: bool = False
    history: list[SagaChatTurn] = Field(default_factory=list, max_length=8)


class SensorAnalysisInput(BaseModel):
    provider: Literal["service_hub", "groq"] = "service_hub"
    question: str = Field(default="", max_length=1200)
    time_s: float | None = Field(default=None, ge=0)
    direct: bool = False


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
_process_runtimes: dict[str, ProcessRuntime] = {}
_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="h2station")
_saga_token_sink: ContextVar[Callable[[str], None] | None] = ContextVar("saga_token_sink", default=None)


def _analyze_frame(frame: dict[str, Any]) -> dict[str, Any]:
    """Turn live process signals into a compact operator-facing assessment."""
    pressure = max(float(frame.get("vehicle_pressure_mpa", 0.0)), float(frame.get("vehicle_2_pressure_mpa", 0.0)))
    temperature = max(float(frame.get("vehicle_temperature_c", 25.0)), float(frame.get("vehicle_2_temperature_c", 25.0)))
    leak = float(frame.get("total_leak_flow_g_s", 0.0))
    esd = bool(frame.get("esd", False))
    active_faults = list(frame.get("active_faults") or [])
    fire_inputs = [fault for fault in active_faults if fault.startswith("external-fire:")]
    flame_signals = frame.get("flame_detectors") or {}
    confirmed_flames = [tag for tag, signal in flame_signals.items()
                        if isinstance(signal, dict) and signal.get("quality") == "GOOD"
                        and float(signal.get("value") or 0.0) >= 0.5]
    fire_detection = {"status": "DETECTED" if confirmed_flames else "PENDING" if fire_inputs else "NONE",
                      "detector_tags": confirmed_flames, "scenario_inputs": fire_inputs,
                      "virtual": True}
    detector_values = [float(x.get("value", 0.0)) for x in (frame.get("gas_detectors") or {}).values() if isinstance(x, dict)]
    max_detector = max(detector_values, default=0.0)
    findings: list[str] = []
    score = 0
    hazop_active = (frame.get("hazop") or {}).get("active", [])
    operations = frame.get("process_operations") or {}
    relief_open = (operations.get("relief_open") or {}) if isinstance(operations, dict) else {}
    open_valves = [key for key, is_open in relief_open.items() if is_open]
    relief_names = {"low": "저압 저장뱅크", "medium": "중압 저장뱅크", "high": "고압 저장뱅크",
                    "hose_1": "1번 충전호스", "hose_2": "2번 충전호스",
                    "vehicle_1": "차량 1 탱크", "vehicle_2": "차량 2 탱크"}
    if open_valves:
        releases = (frame.get("hazop") or {}).get("releases") or []
        relief_flow = sum(float(row.get("mass_flow_g_s") or 0.0) for row in releases
                          if str(row.get("release_id", "")).startswith("relief-"))
        locations = ", ".join(relief_names.get(key, key) for key in open_valves)
        findings.append(f"안전밸브 개방: {locations} · 방출 {relief_flow:.2f} g/s · 설비 압력과 피해영향예측 결과 확인")
        score = 3 if any(fault.startswith("external-fire:") for fault in active_faults) else 2
    if hazop_active:
        findings.append(f"센서 이상 징후 {len(hazop_active)}건: 설비 상태와 운전 조건 확인")
        score = max(score, 3 if any(a.get("severity") == "TRIP" for a in hazop_active) else 2)
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
    if fire_inputs:
        findings.append("외부 화재 시나리오 입력 활성: " +
                        (f"화염검지기 {', '.join(confirmed_flames)} 감지 · 온도·압력 확인"
                         if confirmed_flames else "화염검지 신호 미확인 · 온도·압력 추적"))
        score = max(score, 3)
    elif confirmed_flames:
        findings.append(f"화염검지기 {', '.join(confirmed_flames)} 감지: 주변 설비 상태 확인")
        score = max(score, 3)
    if any(fault.startswith("hydrogen-leak:") for fault in active_faults):
        findings.append("수소 누출 입력 활성: 누출량과 가스검지기 신호를 확인")
        score = max(score, 2)
    if active_faults and score == 0:
        findings.append("설비 이상 입력이 공정 상태와 연동됨")
        score = 1
    if esd:
        findings.insert(0, "ESD 래치: 공정 격리 상태")
        score = 3
    status = ("CRITICAL" if score >= 3 else "WARNING" if score >= 2 else "ADVISORY" if score else "NORMAL")
    headline = {"CRITICAL":"즉시 현장 확인 및 피해영향예측 확인", "WARNING":"운전 조건과 검지기 추세 감시", "ADVISORY":"사고 입력 영향 추적 중", "NORMAL":"모든 연결 신호가 정상 범위"}[status]
    return {"status": status, "score": score, "headline": headline, "findings": findings,
            "max_detector_volpct": max_detector, "fire_detection": fire_detection}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _set_job(job_id: str, **changes: Any) -> None:
    with _jobs_lock:
        _jobs[job_id].update(changes)


def _position_live_fault(event: FaultEvent, time_s: float, relative: bool) -> FaultEvent:
    """Anchor a remote delay at the solver step that consumes the command."""
    if relative:
        return replace(event, start_time_s=time_s + event.start_time_s,
                       end_time_s=(time_s + event.end_time_s if event.end_time_s is not None else None))
    if event.start_time_s < time_s:
        shift = time_s - event.start_time_s
        return replace(event, start_time_s=time_s,
                       end_time_s=(event.end_time_s + shift if event.end_time_s is not None else None))
    return event


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
            initial_bank_fill_percent=(
                request.initial_bank_low_fill_percent,
                request.initial_bank_medium_fill_percent,
                request.initial_bank_high_fill_percent,
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
        with _jobs_lock:
            process_runtime = _process_runtimes.get(job_id)
            simulation_clock = _jobs[job_id]["_simulation_clock"]
        if process_runtime is not None:
            built.station.compressor_suction = lambda _time: process_runtime.trailer_state()
            built.simulator.process_runtime = process_runtime
        def apply_runtime_commands(time_s: float) -> None:
            with _jobs_lock:
                job = _jobs[job_id]
                commands = job["pending_fault_commands"]
                if not commands:
                    return
                registry = job["fault_registry"]
                for command, payload in commands:
                    if command in {"add", "add_relative"}:
                        event = _position_live_fault(payload, time_s, command == "add_relative")
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
            realtime_lag_s = None
            simulation_rate_x = None
            if request.continuous:
                # Speed changes affect pacing only; every physical solver step runs.
                realtime_lag_s, simulation_rate_x = simulation_clock.pace(sample.time_s)
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
                        "process_operations": sample.process_operations,
                        "relief_valves_open": [key for key, is_open in
                                               ((sample.process_operations or {}).get("relief_open") or {}).items()
                                               if is_open],
                        "process_activity": sample.process_activity,
                        "realtime_lag_s": realtime_lag_s,
                        "simulation_rate_x": simulation_rate_x,
                        "vehicle_mass_kg": sample.vehicle_mass_kg,
                        "vehicle_2_mass_kg": sample.vehicle_2_mass_kg,
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
                frame["flame_detectors"] = {
                    tag: value for tag, value in signals.items()
                    if str(tag).startswith("FD-") and isinstance(value, dict)
                }
                frame["analysis"] = _analyze_frame(frame)
                frames.append(frame)
                _jobs[job_id]["next_sequence"] = sequence + 1
                # Keep the virtual monitor bounded while allowing it to run indefinitely.
                if len(frames) > 12000:
                    del frames[:len(frames) - 12000]
                _jobs[job_id]["hazop_detail"] = hazop_monitor.latest
                if process_runtime is not None:
                    _jobs[job_id]["operations"] = process_runtime.snapshot()
                if request.continuous:
                    _jobs[job_id]["realtime_lag_s"] = realtime_lag_s
                    _jobs[job_id]["simulation_rate_x"] = simulation_rate_x

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
            for key in ("analysis", "gas_detectors", "flame_detectors", "released_mass_kg", "peak_vehicle_temperature_c", "trip_causes"):
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
            result["flame_detectors"] = last_frame.get("flame_detectors", {})
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
        "solver": "SciPy LSODA (operator mode) / BDF (legacy mode)",
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
    process_runtime = ProcessRuntime(request.process_settings.model_dump()) if request.process_settings is not None else None
    simulation_clock = SimulationClock(request.speed_multiplier)
    with _jobs_lock:
        if process_runtime is not None:
            _process_runtimes[job_id] = process_runtime
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
            "speed_multiplier": request.speed_multiplier,
            "_simulation_clock": simulation_clock,
            "simulated_time_s": 0.0,
            "total_steps": int(np.ceil(request.duration_s / request.control_period_s)),
            "solver_step": 0,
            "frames": [],
            "next_sequence": 0,
            "stop_requested": False,
            "pending_fault_commands": [],
            "fault_registry": {fault.event_id: fault.to_event() for fault in request.faults},
            "operations": process_runtime.snapshot() if process_runtime is not None else None,
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
            if key not in {"result", "frames", "hazop_detail", "pending_fault_commands", "fault_registry", "_simulation_clock"}
        }


@app.get("/api/simulations/{job_id}/frames")
def simulation_frames(job_id: str, after: int = -1) -> dict[str, Any]:
    """Resume telemetry over HTTP when WebSocket transport is unavailable."""
    with _jobs_lock:
        job = _jobs.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Simulation not found")
        return {
            "job": {k: v for k, v in job.items() if k not in {"result", "frames", "hazop_detail", "pending_fault_commands", "fault_registry", "_simulation_clock"}},
            "frames": [f for f in job.get("frames", []) if f["sequence"] > after],
        }


@app.get("/api/simulations/{job_id}/operations")
def get_process_operations(job_id: str) -> dict[str, Any]:
    with _jobs_lock:
        if job_id not in _jobs:
            raise HTTPException(status_code=404, detail="Simulation not found")
        runtime = _process_runtimes.get(job_id)
        if runtime is None:
            raise HTTPException(status_code=409, detail="This simulation has no operator process mode")
        return runtime.snapshot()


@app.put("/api/simulations/{job_id}/speed")
def set_simulation_speed(job_id: str, request: SimulationSpeedInput) -> dict[str, Any]:
    with _jobs_lock:
        job = _jobs.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Simulation not found")
        if not job["continuous"] or job["status"] not in {"queued", "running"}:
            raise HTTPException(status_code=409, detail="Speed can only change during continuous monitoring")
        latest_sim_s = float(job.get("last_sample_time_s") or 0.0)
        job["_simulation_clock"].set_speed(request.speed_multiplier, latest_sim_s)
        job["speed_multiplier"] = request.speed_multiplier
        job["simulation_rate_x"] = None
        job["realtime_lag_s"] = None
        job["updated_at"] = _utc_now()
        return {"speed_multiplier": request.speed_multiplier, "simulated_time_s": latest_sim_s}


@app.put("/api/simulations/{job_id}/operations")
def set_process_operations(job_id: str, settings: ProcessSettings) -> dict[str, Any]:
    with _jobs_lock:
        job = _jobs.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Simulation not found")
        if job["status"] not in ("queued", "running"):
            raise HTTPException(status_code=409, detail="Simulation is not running")
        runtime = _process_runtimes.get(job_id)
        if runtime is None:
            raise HTTPException(status_code=409, detail="This simulation has no operator process mode")
        try:
            runtime.configure(settings.model_dump())
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        job["operations"] = runtime.snapshot()
        job["updated_at"] = _utc_now()
        return job["operations"]


@app.get("/api/simulations/{job_id}/faults")
def list_simulation_faults(job_id: str) -> dict[str, Any]:
    with _jobs_lock:
        job = _jobs.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Simulation not found")
        time_s = float(job.get("simulated_time_s", 0.0))
        events = [(event, False) for event in job["fault_registry"].values()] + [
            (payload, command == "add_relative") for command, payload in job["pending_fault_commands"]
            if command in {"add", "add_relative"}
        ]
        return {"time_s": time_s, "faults": [
            {"event_id": event.event_id, "kind": event.kind.value, "target": event.target,
             "start_time_s": event.start_time_s + (time_s if relative else 0.0),
             "end_time_s": (event.end_time_s + (time_s if relative else 0.0)
                            if event.end_time_s is not None else None),
             "active": not relative and event.active_at(time_s)}
            for event, relative in events if relative or event.end_time_s is None or event.end_time_s > time_s
        ]}


def _invoke_saga(prompt: str, answer_length: str = "concise", provider: str = "service_hub") -> dict[str, Any]:
    saga_url = os.getenv("H2STATION_SAGA_URL", "http://127.0.0.1:8090").rstrip("/") + "/api/chat"
    body = json.dumps({"message": prompt[:9900], "mode": "chat", "answer_length": answer_length,
                       "provider": provider},
                      ensure_ascii=False).encode("utf-8")
    with urlopen(Request(saga_url, data=body, headers={"Content-Type": "application/json"}), timeout=35) as response:
        return json.load(response)


def _invoke_saga_stream(prompt: str, answer_length: str, provider: str,
                        on_token: Callable[[str], None]) -> dict[str, Any]:
    """Forward SAGA's real chat deltas while retaining its reviewed final answer."""
    saga_url = os.getenv("H2STATION_SAGA_URL", "http://127.0.0.1:8090").rstrip("/") + "/api/chat/stream"
    body = json.dumps({"message": prompt[:9900], "mode": "chat", "answer_length": answer_length,
                       "provider": provider}, ensure_ascii=False).encode("utf-8")
    final: dict[str, Any] | None = None
    event_name = ""
    data_lines: list[str] = []
    with urlopen(Request(saga_url, data=body, headers={"Content-Type": "application/json"}), timeout=120) as response:
        for raw_line in response:
            line = raw_line.decode("utf-8").rstrip("\r\n")
            if line.startswith("event:"):
                event_name = line[6:].strip()
            elif line.startswith("data:"):
                data_lines.append(line[5:].strip())
            elif not line and data_lines:
                payload = json.loads("\n".join(data_lines))
                if event_name in {"draft_token", "token"}:
                    on_token(str(payload.get("text") or ""))
                elif event_name == "answer":
                    final = payload
                elif event_name == "error":
                    raise URLError(str(payload.get("detail") or "SAGA 스트림 오류"))
                event_name = ""
                data_lines.clear()
    if final is None:
        raise URLError("SAGA 스트림에서 최종 답변을 받지 못했습니다.")
    return final


async def _invoke_saga_selected(prompt: str, answer_length: str, provider: str,
                                explicit_length: bool = False,
                                stream_output: bool = False) -> dict[str, Any]:
    sink = _saga_token_sink.get() if stream_output else None
    if sink is not None:
        return await asyncio.to_thread(_invoke_saga_stream, prompt, answer_length, provider, sink)
    # Preserve the existing two-argument path for default requests and test doubles.
    if provider == "groq":
        return await asyncio.to_thread(_invoke_saga, prompt, answer_length, provider)
    if answer_length == "concise" and not explicit_length:
        return await asyncio.to_thread(_invoke_saga, prompt)
    return await asyncio.to_thread(_invoke_saga, prompt, answer_length)


def _stream_analysis_response(run: Callable[[], Awaitable[dict[str, Any]]],
                              starting_status: str) -> StreamingResponse:
    async def events():
        queue: asyncio.Queue[tuple[str, dict[str, Any]]] = asyncio.Queue()
        loop = asyncio.get_running_loop()
        emitted_tokens = 0

        def send_token(value: str) -> None:
            if value:
                loop.call_soon_threadsafe(queue.put_nowait, ("token", {"text": value}))

        async def selected_run() -> dict[str, Any]:
            token = _saga_token_sink.set(send_token)
            try:
                return await run()
            finally:
                _saga_token_sink.reset(token)

        task = asyncio.create_task(selected_run())
        yield f"event: status\ndata: {json.dumps({'text': starting_status}, ensure_ascii=False)}\n\n"
        try:
            while not task.done() or not queue.empty():
                try:
                    event_name, payload = await asyncio.wait_for(queue.get(), timeout=0.25)
                except asyncio.TimeoutError:
                    continue
                if event_name == "token":
                    emitted_tokens += 1
                yield f"event: {event_name}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
            result = await task
            if not emitted_tokens:
                # The deterministic endpoint returns one result. Reveal that
                # result progressively in the same SSE UI, without invoking
                # the generative/reasoning API just to obtain token events.
                answer = str(result.get("analysis_answer") or result.get("answer") or "")
                for offset in range(0, len(answer), 48):
                    yield f"event: token\ndata: {json.dumps({'text': answer[offset:offset + 48]}, ensure_ascii=False)}\n\n"
                    await asyncio.sleep(0.012)
            yield f"event: result\ndata: {json.dumps(result, ensure_ascii=False, default=str)}\n\n"
        except Exception as exc:
            detail = exc.detail if isinstance(exc, HTTPException) else str(exc)
            yield f"event: error\ndata: {json.dumps({'detail': detail}, ensure_ascii=False)}\n\n"
        finally:
            if not task.done():
                task.cancel()

    return StreamingResponse(events(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


def _invoke_saga_hazop_direct(
    frame: dict[str, Any], catalog: dict[str, Any], station_id: str, question: str = "",
    impact_results: list[dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    """Send one simulator snapshot to SAGA's deterministic HAZOP endpoint.

    This call deliberately does not use ``/api/chat``. It transfers the
    simulator's own HAZOP rows and current signals, so SAGA can answer with
    numeric comparisons and row-level emergency actions without waiting for
    an LLM, RAG search, or review pass.
    """
    signals = (frame.get("hazop") or {}).get("signals") or {}
    if not isinstance(signals, dict):
        return None
    readings: list[dict[str, Any]] = []
    signal_tags: set[str] = set()
    for tag, raw in signals.items():
        if not isinstance(raw, dict) or raw.get("value") is None:
            continue
        try:
            value = float(raw.get("value"))
        except (TypeError, ValueError):
            continue
        if not np.isfinite(value):
            continue
        signal_tags.add(str(tag))
        readings.append({
            "tagId": str(tag),
            "value": value,
            "unit": str(raw.get("unit") or ""),
            "quality": str(raw.get("quality") or "GOOD"),
        })
    if not readings:
        return None
    # Transfer only rows that can be evaluated against this snapshot. This
    # keeps the request small even when the catalogue grows beyond 205 rows.
    rules = [
        row for row in (catalog.get("rules") or [])
        if isinstance(row, dict) and str(row.get("sensor_id") or row.get("센서_ID") or "") in signal_tags
    ]
    equipment = [
        {
            "equipmentId": str(node.get("node_id")),
            "name": str(node.get("설비_라인") or node.get("name") or ""),
            "equipmentType": "digital-twin-node",
        }
        for node in (catalog.get("nodes") or [])
        if isinstance(node, dict) and node.get("node_id")
    ]
    body = json.dumps({
        "stationId": station_id,
        "scenarioId": "*",
        "readings": readings,
        "equipment": equipment,
        "hazopRules": rules,
        "condition": question[:1200],
        "impactResults": impact_results or [],
        "interpret": False,
        "generateSop": True,
        "maxStalenessSeconds": 86400,
    }, ensure_ascii=False, default=str).encode("utf-8")
    saga_url = os.getenv("H2STATION_SAGA_DIRECT_URL")
    if not saga_url:
        saga_url = os.getenv("H2STATION_SAGA_URL", "http://127.0.0.1:8090").rstrip("/") + "/api/digital-twin/hazop/direct"
    try:
        with urlopen(Request(saga_url, data=body, headers={"Content-Type": "application/json"}), timeout=3) as response:
            result = json.load(response)
        return result if isinstance(result, dict) else None
    except (URLError, HTTPError, TimeoutError, OSError, ValueError):
        # A stopped or older SAGA process must not make the digital twin unavailable.
        return None


def _direct_hazop_answer(result: dict[str, Any]) -> str:
    sop = result.get("sop") if isinstance(result.get("sop"), dict) else {}
    answer = str(sop.get("answer") or "").strip()
    if answer:
        return answer
    status = str(result.get("status") or "UNKNOWN")
    hits = result.get("hits") if isinstance(result.get("hits"), list) else []
    if status == "NORMAL":
        return "현재 전달된 센서값은 전송된 HAZOP 수치 기준을 넘지 않았습니다. 다음 측정 주기와 알람 상태를 계속 감시하세요."
    if hits:
        labels = [str(item.get("item_name") or item.get("tag_id") or "조건") for item in hits[:5] if isinstance(item, dict)]
        return "현재 HAZOP 수치 기준을 초과한 조건이 감지되었습니다: " + ", ".join(labels)
    return "현재 스냅샷은 일부 HAZOP 기준과 연결되지 않아 상태를 완전한 정상으로 확정할 수 없습니다."


def _direct_impact_summary(results: list[dict[str, Any]]) -> str:
    """Report only computed sample results, with their measured basis visible."""
    if not results:
        return ""
    lines = ["### 피해영향예측 · 현재 센서 기준"]
    for row in results[:3]:
        node = str(row.get("node_name") or row.get("node_id") or "설비")
        pressure = row.get("current_pressure_mpa")
        temperature = row.get("current_temperature_c")
        basis = "현재 모의 누출" if row.get("calculation_basis") == "ACTIVE_RELEASE_CURRENT_SENSORS" else "가정 누출"
        measured = []
        if isinstance(pressure, (int, float)):
            measured.append(f"{row.get('pressure_sensor') or '압력'} {pressure:g} MPa")
        if isinstance(temperature, (int, float)):
            measured.append(f"{row.get('temperature_sensor') or '온도'} {temperature:g} °C")
        diameter = row.get("orifice_diameter_mm")
        if isinstance(diameter, (int, float)):
            measured.append(f"누출 구경 {diameter:g} mm")
        lines.append(f"- **{node}** ({basis}): " + ", ".join(measured))
        effect = []
        heat = row.get("maximum_heat_flux_w_m2")
        pressure_pa = row.get("maximum_overpressure_pa")
        if isinstance(heat, (int, float)):
            effect.append(f"최대 열복사 {heat / 1000:g} kW/m²")
        if isinstance(pressure_pa, (int, float)):
            effect.append(f"최대 과압 {pressure_pa / 1000:g} kPa")
        radius = row.get("sampled_effect_radius_m")
        if isinstance(radius, (int, float)) and radius > 0:
            next_sample = row.get("sampled_next_distance_m")
            detail = f"기준 초과 최원거리 표본점 {radius:g} m"
            if isinstance(next_sample, (int, float)) and next_sample > radius:
                detail += f" · 다음 표본점 {next_sample:g} m는 기준 미달"
            effect.append(detail)
        else:
            effect.append("표본점 기준 초과 거리 미확정")
        lines.append("  " + " · ".join(effect))
    lines.append("표본점 결과는 현장 안전거리나 확정 대피반경이 아닙니다.")
    return "\n".join(lines)


def _safe_saga_text(answer: str) -> str:
    """Remove generic calculation requests and claims of a certified radius."""
    answer = re.sub(r"(?<![A-Za-z0-9_])(?:SENSOR_BASED_(?:PROXY_)?|LLM_PROPOSED_(?:PROXY_)?)HYPOTHESIS(?![A-Za-z0-9_])",
                    "센서 기준 가정 누출", answer)
    answer = re.sub(r"(?<![A-Za-z0-9_])ACTIVE_RELEASE_CURRENT_SENSORS(?![A-Za-z0-9_])", "현재 누출", answer)
    answer = re.sub(r"(?<![A-Za-z0-9_])calculated(?![A-Za-z0-9_])", "계산 완료", answer, flags=re.IGNORECASE)
    unsafe_radius = re.compile(r"(?:안전\s*반경|영향\s*반경).{0,50}(?:확정|보장|안전)|(?:확정|안전).{0,30}(?:안전\s*반경|영향\s*반경)")
    def allowed(line: str) -> bool:
        if line.lstrip().startswith("※ 일반 대화 모드"):
            return False
        if re.search(r"HAZOP|LATCHED|HZ[-‑–]\d+|HY[-‑–]\d+|rule_id|\bDB\b|규칙", line, re.IGNORECASE):
            return False
        if any(term in line for term in ("요청되지 않았", "요청하지 않았", "실행되지 않았", "아직 계산되지", "계산 결과를 제공하지")) and any(
            term in line.lower() for term in ("피해영향", "영향평가", "impact_results", "hyram")
        ):
            return False
        compact = re.sub(r"[\s`'\"‘’“”·]", "", line).lower()
        deferred_calculation = (any(term in compact for term in ("피해영향", "hyram", "영향범위"))
            and (bool(re.search(r"(?:계산|평가)(?:이|을|를)?(?:필요|요청|권장|해보|하시|실행)", compact))
                 or ("필요시" in compact and "계산" in compact and "요청" in compact)))
        return not deferred_calculation and not unsafe_radius.search(line)
    return "\n".join(line for line in answer.splitlines() if allowed(line)).strip()


def _impact_requested(question: str) -> bool:
    return any(term in question for term in ("피해", "영향", "누출", "사고 범위", "위험 범위", "시나리오"))


def _normal_monitoring_text(answer: str) -> str:
    """Keep routine, healthy-state answers focused on current operation."""
    impact_terms = ("피해영향", "영향 반경", "영향반경", "안전반경", "사고 범위", "열복사", "과압",
                    "가정 누출", "가상 누출", "impact_results", "계산 실패", "입력 부족",
                    "IntegratorConcurrencyError", "LATCHED", "HY-")
    lines = [line for line in answer.splitlines() if not any(term.lower() in line.lower() for term in impact_terms)]
    return "\n".join(lines).strip() or "현재 센서 상태를 확인했습니다. 활성 주의·경보는 없습니다."


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


async def _run_saga_scenario_analysis(
    frame: dict[str, Any], catalog: dict[str, Any], backend: Any,
    request: SagaAnalysisInput, active: list[dict[str, Any]],
    mentioned_ids: set[str], sensor_count: int,
) -> dict[str, Any]:
    hypothetical_guidance = response_selection(frame, catalog, request.question + " 가정 누출", "manual")
    guidance_text = render_guidance(hypothetical_guidance, actual_alert=False)
    source_inputs = available_sensor_inputs(frame, catalog)
    if not source_inputs["pressure"] or not source_inputs["temperature"]:
        summary = "현재 사용할 수 있는 압력 또는 온도 센서값이 전혀 없어 수치 계산을 수행하지 않았습니다."
        return {"time_s": frame.get("time_s"), "trigger": request.trigger,
                "scenario_mode": True,
                "answer": summary + ("\n\n---\n\n" + guidance_text if guidance_text else ""),
                "analysis_answer": summary,
                "response_guidance": structured_guidance(hypothetical_guidance, actual_alert=False),
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
        plan_reply = await _invoke_saga_selected(plan_prompt, "concise", request.provider)
        try:
            proposals = parse_saga_plan(str(plan_reply.get("answer") or ""), eligible_ids, catalog,
                                        pressure_tags, temperature_tags)
        except ValueError as exc:
            retry_prompt = plan_prompt[:7300] + (f"\n이전 출력은 검증 실패({exc})였습니다. 다시 JSON 객체만 출력하세요.\n"
                + str(plan_reply.get("answer") or "")[:450])
            plan_reply = await _invoke_saga_selected(retry_prompt, "concise", request.provider)
            proposals = parse_saga_plan(str(plan_reply.get("answer") or ""), eligible_ids, catalog,
                                        pressure_tags, temperature_tags)
    except (URLError, HTTPError, TimeoutError, OSError) as exc:
        raise HTTPException(status_code=503, detail=f"SAGA 시나리오 제안 실패: {exc}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=f"SAGA 시나리오 형식 검증 실패: {exc}") from exc
    results = await asyncio.to_thread(assess_sensor_cases, frame, catalog, backend, [], proposals=proposals)
    calculated_results = [row for row in results if row.get("calculation_status") == "calculated"]
    if not calculated_results:
        summary = "제안한 가상 시나리오의 피해영향예측 수치 결과를 얻지 못했습니다. 현재 운전 중 사고가 발생했다는 뜻은 아닙니다."
        return {"time_s": frame.get("time_s"), "trigger": request.trigger,
                "scenario_mode": True, "show_impact_results": False,
                "answer": summary + ("\n\n---\n\n" + guidance_text if guidance_text else ""),
                "analysis_answer": summary,
                "response_guidance": structured_guidance(hypothetical_guidance, actual_alert=False),
                "model": plan_reply.get("model", ""), "proposed_scenarios": proposals,
                "impact_results": [], "active_rule_ids": sorted(rule_ids - {None}),
                "sensor_count": sensor_count}
    interpretation_context = {"time_s": frame.get("time_s"), "question": request.question,
                              "proposed_scenarios": proposals, "impact_results": calculated_results,
                              "emergency_response_guidance": prompt_guidance(hypothetical_guidance),
                              "active_hazop": active[:15], "hazop_rules": rules,
                              "scenario_is_hypothetical": True, "process_fault_injected": False}
    interpretation_prompt = (
        "당신이 제안한 가상 누출 시나리오를 서버가 현재 GOOD 품질 센서값으로 피해영향예측 계산했습니다. "
        "아래 실제 계산 결과만 해석하세요. 계산을 다시 권하지 마세요. 사고가 실제 발생했다고 말하지 마세요. "
        "계산이 완료된 시나리오의 선택 이유, 센서값, 열복사·과압, 표본 거리의 차이를 설명하세요. "
        "sensor_basis=PROXY이면 대체 센서의 태그와 원래 노드를 밝히고 목표 설비의 직접 계측값으로 표현하지 마세요. "
        "대체 신호로 계산된 경우 누락 입력을 나열하거나 추가 입력을 요구하지 말고 실제 사용한 태그·출처·가정만 밝히세요. "
        "sampled_effect_radius_m은 임계값을 초과한 최원거리 관측점일 뿐, 안전반경이나 최대 사고범위가 아닙니다. "
        "sampled_next_distance_m이 있으면 다음 관측점에서는 기준 미달임을 함께 설명하세요. 두 표본 사이의 정확한 경계는 계산되지 않았습니다. "
        "null이면 범위가 미확정입니다. 제공되지 않은 시나리오의 수치나 실패 이유를 만들지 마세요. "
        "내부 분석 방식, HAZOP, 규칙 ID, DB 상태, LATCHED 같은 구현 정보는 사용자에게 밝히지 마세요. 현재 센서와 운전 상태만 자연스럽게 설명하세요. "
        "가상 사고가 실제 발생할 경우의 대응 우선순위를 제공된 대응 자료에 따라 요약하세요. 자료 밖의 절차나 확정 대피거리를 만들지 마세요. 상세 단계는 서버가 별도로 표시합니다. "
        "사용자에게는 엔진 제품명 대신 '피해영향예측'이라고 쓰세요. 한국어 Markdown으로 간결하게 답하세요.\n"
        + json.dumps(interpretation_context, ensure_ascii=False, default=str)[:8200])
    try:
        interpretation = await _invoke_saga_selected(interpretation_prompt, "standard", request.provider,
                                                     stream_output=True)
    except (URLError, HTTPError, TimeoutError, OSError) as exc:
        raise HTTPException(status_code=503, detail=f"SAGA 계산 결과 해석 실패: {exc}") from exc
    narrative = _safe_saga_text(str(interpretation.get("answer") or ""))
    analysis_answer = narrative or "제안한 가상 누출의 계산 결과를 아래에서 확인할 수 있습니다."
    if guidance_text:
        narrative = (narrative + "\n\n---\n\n" if narrative else "") + guidance_text
    return {"time_s": frame.get("time_s"), "trigger": request.trigger,
            "scenario_mode": True, "show_impact_results": True,
            "answer": narrative or analysis_answer, "analysis_answer": analysis_answer,
            "response_guidance": structured_guidance(hypothetical_guidance, actual_alert=False),
            "model": interpretation.get("model", ""), "proposed_scenarios": proposals,
            "impact_results": calculated_results, "active_rule_ids": sorted(rule_ids - {None}),
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
    rule_fields = ("rule_id", "node_id", "sensor_id", "시나리오명", "연산자", "임계값",
                   "단위", "등급", "원인후보", "사고_전개조건", "HyRAM_case_id")
    matched_rules = [{field: rule.get(field) for field in rule_fields}
                     for rule in catalog["rules"] if rule["rule_id"] in ids]
    mentioned_nodes = _mentioned_hazop_nodes(request.question, catalog)
    mentioned_ids = {node["node_id"] for node in mentioned_nodes}
    reference_rules = [rule for rule in catalog["rules"] if rule["node_id"] in mentioned_ids]
    signal_prefixes = tuple(prefix for word, prefix in (("압력", "PT-"), ("온도", "TT-"), ("유량", "FT-"), ("가스", "GD-"), ("화염", "FD-"))
        if word in request.question)
    if signal_prefixes:
        filtered_rules = [rule for rule in reference_rules if str(rule["sensor_id"]).startswith(signal_prefixes)]
        if filtered_rules:
            reference_rules = filtered_rules
    reference_rules = reference_rules[:18]
    reference_rules = [{field: rule.get(field) for field in rule_fields} for rule in reference_rules]
    signals = hazop.get("signals") or {}
    sensor_values = {tag: {"value": value.get("value"), "unit": value.get("unit"),
        "quality": value.get("quality")} for tag, value in signals.items()
        if isinstance(value, dict) and (value.get("quality") == "GOOD" or tag.startswith("GD-"))}
    reference_tags = {rule["sensor_id"] for rule in reference_rules}
    releases = hazop.get("releases") or []
    analysis = frame.get("analysis") or _analyze_frame(frame)
    alert_status = str(analysis.get("status") or "NORMAL")
    if alert_status == "NORMAL" and (active or releases or frame.get("active_faults")
                                      or frame.get("relief_valves_open")):
        derived = _analyze_frame(frame)
        alert_status = str(derived.get("status") or "NORMAL")
        if alert_status == "NORMAL":
            alert_status = "WARNING"
        analysis = {**analysis, "status": alert_status,
                    "findings": analysis.get("findings") or derived.get("findings") or []}
    emergency_context = (alert_status != "NORMAL" or bool(active or releases)
                         or bool(frame.get("active_faults") or frame.get("relief_valves_open"))
                         or bool((analysis.get("fire_detection") or {}).get("detector_tags")))
    show_impact_results = (emergency_context
                           or (request.trigger == "manual" and _impact_requested(request.question)))
    if request.scenario_mode or (not request.direct and _scenario_requested(request)):
        backend = await asyncio.to_thread(load_hyram_backend)
        return await _run_saga_scenario_analysis(frame, catalog, backend, request, active,
                                                 mentioned_ids, len(sensor_values))
    response_plans = response_selection(frame, catalog, request.question, request.trigger)
    sensor_impacts = []
    backend = None
    if show_impact_results:
        backend = await asyncio.to_thread(load_hyram_backend)
        active_nodes = [str(row.get("node_id")) for row in active if isinstance(row, dict) and row.get("node_id")]
        release_nodes = [node["node_id"] for release in releases if isinstance(release, dict)
            for node in catalog["nodes"] if node.get("누출_target") == release.get("component_id")]
        fault_targets = [str(fault).split(":", 1)[1] for fault in (frame.get("active_faults") or [])
            if isinstance(fault, str) and ":" in fault]
        fault_node_aliases = {"compressor": ["N06"], "precooler": ["N19"], "pcv": ["N11", "N15"],
                              "header": ["N10"], "cascade": ["N07", "N08", "N09"],
                              "supply": ["N01", "N02"], "station": ["N10"]}
        fault_nodes = [node["node_id"] for target in fault_targets for node in catalog["nodes"]
            if node.get("누출_target") == target]
        fault_nodes += [node_id for target in fault_targets for node_id in fault_node_aliases.get(target, [])]
        candidates = ([node["node_id"] for node in mentioned_nodes] + fault_nodes + release_nodes + active_nodes
                      if request.trigger == "manual" else fault_nodes + release_nodes + active_nodes)
        if not candidates:
            # A status-only alarm can have no active rule row. Choose a
            # reference case from the GOOD P/T pairs that actually exist in
            # this frame instead of assuming the high bank is instrumented.
            available = available_sensor_inputs(frame, catalog)
            pressure_nodes = {row["node_id"] for row in available["pressure"]}
            temperature_nodes = {row["node_id"] for row in available["temperature"]}
            usable_nodes = pressure_nodes & temperature_nodes
            preferred = ["N09", "N08", "N07", "N13", "N17", "N06"]
            case_nodes = {row["node_id"] for row in catalog["cases"]}
            candidates = [node_id for node_id in preferred if node_id in usable_nodes and node_id in case_nodes]
            candidates += [node["node_id"] for node in catalog["nodes"]
                           if node["node_id"] in usable_nodes and node["node_id"] in case_nodes
                           and node["node_id"] not in candidates]
            candidates = candidates[:3]
        sensor_impacts = await asyncio.to_thread(assess_sensor_cases, frame, catalog, backend, candidates)
    legacy_impacts = [{"release_id": release.get("release_id"),
        "component_id": release.get("component_id"),
        "mass_flow_g_s": release.get("mass_flow_g_s"),
        "calculation_status": (release.get("consequence") or {}).get("status"),
        "maximum_heat_flux_w_m2": (release.get("consequence") or {}).get("maximum_heat_flux_w_m2"),
        "maximum_overpressure_pa": (release.get("consequence") or {}).get("maximum_overpressure_pa"),
        "sampled_effect_radius_m": ((release.get("consequence") or {}).get("sampled_effect_radius_m") or None),
        "sampled_max_distance_m": (release.get("consequence") or {}).get("sampled_max_distance_m"),
        "sampled_next_distance_m": (release.get("consequence") or {}).get("sampled_next_distance_m"),
        "observation_point_count": (release.get("consequence") or {}).get("observation_point_count"),
        "effect_range_status": (release.get("consequence") or {}).get("effect_range_status"),
        "range_interpretation": ("표본 관측점에서 5 kW/m² 및 5 kPa 기준 미달; 영향 반경 미확정"
            if (release.get("consequence") or {}).get("effect_range_status") == "BELOW_THRESHOLDS_AT_SAMPLES"
            else "관측점의 임계값 초과 거리만 확인; 현장 안전반경 아님")}
        for release in releases[:5] if isinstance(release, dict)]
    assessed_releases = {row.get("release_id") for row in sensor_impacts if row.get("calculation_status") == "calculated"}
    impact_results = [row for row in sensor_impacts + [row for row in legacy_impacts
        if row.get("release_id") not in assessed_releases]
        if row.get("calculation_status") == "calculated"]
    if request.direct:
        # Keep the live monitor on the dedicated low-latency API even for
        # alarms. Consequences are calculated first from this same snapshot;
        # an unavailable SAGA process falls back to local deterministic data,
        # never to the slower generative chat endpoint.
        direct_result = await asyncio.to_thread(
            _invoke_saga_hazop_direct, frame, catalog, str(job_id), request.question, impact_results
        )
        direct_sop = (direct_result or {}).get("sop") if isinstance((direct_result or {}).get("sop"), dict) else {}
        direct_hits = (direct_result or {}).get("hits") if isinstance((direct_result or {}).get("hits"), list) else []
        actual_alert = emergency_context or bool(direct_hits)
        if direct_result:
            answer = _safe_saga_text(_direct_hazop_answer(direct_result))
        else:
            answer = ""
        if actual_alert and re.search(r"(?:정상\s*운전|정상\s*범위|이상\s*없|경보\s*없)", answer):
            answer = ""
        if not answer:
            findings = [str(item) for item in (analysis.get("findings") or [])[:3]]
            answer = ("현재 주의·경보 신호를 확인했습니다. " + " · ".join(findings)
                      if actual_alert else "현재 센서와 설비 신호를 확인했습니다. 정상 운전 상태입니다.")
        if actual_alert and alert_status == "NORMAL":
            alert_status = "WARNING"
        impact_text = _direct_impact_summary(impact_results) if show_impact_results else ""
        if impact_text:
            answer += "\n\n" + impact_text
        elif show_impact_results:
            answer += "\n\n현재 센서 기준 정량 피해영향 결과는 확보되지 않았습니다."
        analysis_answer = answer
        guidance = render_guidance(response_plans, actual_alert=actual_alert)
        if guidance:
            answer += "\n\n---\n\n" + guidance
        return {
            "time_s": frame.get("time_s"), "trigger": request.trigger,
            "answer": answer, "analysis_answer": analysis_answer,
            "response_guidance": structured_guidance(response_plans, actual_alert=actual_alert),
            "model": "SAGA 직답 · 센서 기반 계산",
            "active_rule_ids": sorted(ids), "sensor_count": len(sensor_values),
            "risk_assessment": {"status": alert_status, "score": analysis.get("score"),
                                "findings": analysis.get("findings") or [],
                                "calculated_impact_count": len(impact_results)},
            "show_impact_results": show_impact_results,
            "impact_results": impact_results,
            "hazop_direct": direct_result,
            "hazop_sop": direct_sop,
            "hazop_hit_count": len(direct_hits),
        }
    context = {"impact_results":impact_results,
        "impact_calculation_attempted":show_impact_results,
        "station":"H70 reference simulation", "time_s":frame.get("time_s"),
        "fire_detection": analysis.get("fire_detection"),
        "flame_detector_signals": frame.get("flame_detectors") or {},
        "active_faults":frame.get("active_faults"),
        "analysis":analysis,
        "emergency_response_guidance":prompt_guidance(response_plans),
        "relief_valves_open":frame.get("relief_valves_open") or [],
        "relief_valve_settings":{key: value for key, value in
            (((frame.get("process_operations") or {}).get("settings") or {}).get("relief_valves") or {}).items()
            if key in (frame.get("relief_valves_open") or [])},
        "hazop_active":active, "hazop_rules":matched_rules,
        "hazop_reference_rules":reference_rules,
        "reference_sensor_values":{tag: value for tag, value in sensor_values.items() if tag in reference_tags},
        "sensor_values":sensor_values,
        "hazop_nodes":[{"node_id": node["node_id"], "name": node.get("설비_라인")} for node in catalog["nodes"]],
        "impact_backend_available":bool(getattr(backend,"available",False)),
        "current_alert_status":alert_status,
        "active_hazop_rule_count":len(active)}
    history = "\n".join(f"{turn.role}: {turn.content}" for turn in request.history)[-1800:]
    prompt = ("당신은 H70 수소충전소 운전 분석 보조자입니다. 아래 데이터는 실제 현장 계측이 아닌 시뮬레이터 신호입니다. "
        "HAZOP 센서 임계값과 현재 신호 품질, 물리 누출 및 피해영향예측 계산 상태를 구분하세요. "
        "external-fire 사고 입력은 화염검지기의 감지 신호가 아닙니다. fire_detection.status=DETECTED이고 FD 신호가 GOOD일 때에만 해당 구역 화염검지라고 쓰세요. "
        "현재 FD 신호는 주입 사고에서 계산한 가상 검지 대리값으로, 독립 실측이나 광학 시야 검증이 아닙니다. PENDING이면 화재 시나리오 입력과 검지 미확인을 명확히 구분하세요. "
        + ("현재 주의·경보에 대응하여 서버가 현재 센서값으로 피해영향예측을 먼저 수행했습니다. impact_results의 계산 완료 항목과 사용 센서를 구체적으로 해석하고 계산을 다시 권하지 마세요. "
           if emergency_context and impact_results else
           "현재 주의·경보에 대응하여 서버가 피해영향예측을 시도했지만 정량 결과가 확보되지 않았습니다. 결과 수치를 만들거나 재계산을 권하지 말고 현재 위험상태와 우선 조치를 설명하세요. "
           if emergency_context else
           "정상 운전에서는 사용자가 사고 영향을 요청한 경우에만 계산 결과를 설명하세요. 요청하지 않았다면 사고 수치를 언급하지 마세요. ") +
        "impact_results의 계산 성공 항목만 수치 결과로 설명하세요. "
        "calculation_basis=SENSOR_BASED_HYPOTHESIS는 실제 누출이 아닌 1 mm 가정 시나리오이며, ACTIVE_RELEASE_CURRENT_SENSORS는 현재 물리 누출입니다. 둘을 혼동하지 마세요. "
        "calculation_status=calculated이면 이미 계산된 값입니다. 피해영향 계산이나 엔진 실행을 사용자에게 권하거나 요청하지 마세요. "
        "계산되지 않은 항목의 입력 부족이나 재계산 요청을 나열하지 마세요. 사용한 센서 태그와 출처·가정은 밝히세요. "
        "relief_valves_open에 항목이 있으면 안전밸브 개방을 현재 운전 경고로 분명히 알리고, 해당 밸브의 개방 압력·실제 방출 및 이미 계산된 피해영향을 함께 해석하세요. 안전밸브 방출을 임의의 배관 파손으로 단정하지 마세요. "
        "sampled_effect_radius_m이 null이면 표본 관측점에서 기준 미달입니다. 이때 숫자 반경을 만들지 말고 '표본 관측점에서 기준 미달, 영향 반경 미확정'이라고 쓰세요. "
        "sampled_effect_radius_m이 양수이고 sampled_next_distance_m이 있으면 기준 초과 최원거리 표본점과 다음 기준 미달 표본점을 함께 말하세요. 현장 안전거리로 단정하지 마세요. "
        "계산 결과가 없으면 사고 범위를 추정값처럼 제시하지 마세요. 계산이 요청되지 않았다는 문구를 출력하지 마세요. 제공된 HAZOP 규칙에 없는 규칙 ID나 임계값을 만들지 마세요. "
        "사용자에게는 계산기 제품명 대신 '피해영향예측'이라고 표기하세요. "
        "내부 규칙이나 DB 명칭을 밝히지 말고 센서값, 설비 상태, 주의 원인과 운전 조치만 설명하세요. "
        "emergency_response_guidance가 있으면 현재 신호와 연결한 대응 우선순위를 요약하세요. 자료 밖의 절차를 만들지 마세요. 상세한 즉시 조치, 안정화 확인, 재가동 조건, 예방·안전관리는 서버가 별도로 표시합니다. "
        "현장 승인 비상계획과 소방 지휘를 우선하고, 모의 영향 반경을 확정 대피거리로 쓰지 마세요. 공급이 계속되는 수소 화염을 임의로 끄도록 권하지 마세요. "
        "current_alert_status와 안전밸브 개방 상태가 현재 경보 상태의 근거입니다. 활성 내부 규칙이 없더라도 안전밸브가 열려 있으면 경보를 유지하세요. "
        "현재 경보 여부와 내부 등록 기준을 구분하세요. 사용자에게는 실제 센서 태그와 운전 상태만 한국어로 간결하게 답하세요. "
        "정상 운전이며 사용자가 피해영향을 요청하지 않았다면 계산값은 내부 판단에만 사용하고 답변에 피해영향 수치·가정 누출 결과를 쓰지 마세요.\n"
        f"요청 유형: {request.trigger}\n이전 대화(현재 센서보다 우선하지 않음):\n{history}\n"
        f"운전자 질문: {request.question}\n현재 데이터 및 HAZOP DB 발췌:\n"
        + json.dumps(context, ensure_ascii=False, default=str)[:7500])[:9900]
    try:
        reply = await _invoke_saga_selected(prompt, "concise", request.provider, stream_output=True)
    except (URLError, HTTPError, TimeoutError, OSError) as exc:
        if not emergency_context:
            raise HTTPException(status_code=503, detail=f"SAGA 연결/분석 실패: {exc}") from exc
        severity_name = {"CRITICAL": "긴급", "WARNING": "경고", "ADVISORY": "주의"}.get(alert_status, alert_status)
        findings = [str(item) for item in (analysis.get("findings") or [])[:3]]
        fallback = [f"현재 위험도: **{severity_name}** (현재 센서·설비 신호 기준)"]
        fallback.extend(f"- {item}" for item in findings)
        if impact_results:
            fallback.append(f"현재 센서 기준 피해영향예측 **{len(impact_results)}건**의 계산값을 아래에 표시합니다.")
        else:
            fallback.append("피해영향 수치가 확정되지 않아 정량 범위를 제시하지 않습니다.")
        reply = {"answer": "\n".join(fallback), "model": "센서 기반 위험 분석"}
    answer = str(reply.get("answer") or "")
    answer = _safe_saga_text(answer)
    if emergency_context:
        answer = "\n".join(line for line in answer.splitlines()
            if not re.search(r"(?:현재\s*(?:운전\s*)?상태는\s*정상|현재\s*운전은\s*정상|정상\s*운전\s*중|경보는\s*없)", line))
    if not show_impact_results:
        answer = _normal_monitoring_text(answer)
    if not answer:
        answer = "현재 센서와 설비 상태를 확인했습니다. 계산 결과는 아래에서 확인할 수 있습니다." if show_impact_results else "현재 센서와 설비 상태를 확인했습니다."
    analysis_answer = answer
    actual_alert = emergency_context
    guidance = render_guidance(response_plans, actual_alert=actual_alert)
    if guidance:
        answer = f"{answer}\n\n---\n\n{guidance}"
    return {"time_s":frame.get("time_s"), "trigger":request.trigger,
        "answer":answer, "analysis_answer":analysis_answer,
        "response_guidance":structured_guidance(response_plans, actual_alert=actual_alert),
        "model":reply.get("model", ""),
        "active_rule_ids":sorted(ids), "sensor_count":len(sensor_values),
        "risk_assessment":{"status":alert_status, "score":analysis.get("score"),
                           "findings":analysis.get("findings") or [],
                           "calculated_impact_count":len(impact_results)},
        "show_impact_results":show_impact_results,
        "impact_results":impact_results}


@app.post("/api/simulations/{job_id}/saga-analysis/stream")
async def saga_analysis_stream(job_id: str, request: SagaAnalysisInput) -> StreamingResponse:
    return _stream_analysis_response(
        lambda: saga_analysis(job_id, request),
        "센서 상태와 피해영향예측 결과를 확인하고 있습니다…" if request.trigger == "alarm"
        else "현재 공정 신호를 분석하고 있습니다…",
    )


@app.post("/api/simulations/{job_id}/faults", status_code=202)
def add_simulation_fault(job_id: str, fault: FaultInput, relative: bool = False) -> dict[str, Any]:
    event = fault.to_event()
    with _jobs_lock:
        job = _jobs.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Simulation not found")
        if job["status"] not in {"queued", "running"} or job.get("stop_requested"):
            raise HTTPException(status_code=409, detail="Simulation is not running")
        if event.event_id in job["fault_registry"] or any(
            command in {"add", "add_relative"} and payload.event_id == event.event_id
            for command, payload in job["pending_fault_commands"]
        ):
            raise HTTPException(status_code=409, detail="Fault event ID already exists")
        job["pending_fault_commands"].append(("add_relative" if relative else "add", event))
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
            command in {"add", "add_relative"} and payload.event_id == event_id
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
                    if key not in {"result", "frames", "hazop_detail", "pending_fault_commands", "fault_registry", "_simulation_clock"}
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


@app.get("/api/hazop/emergency-responses")
def hazop_emergency_responses() -> dict[str, Any]:
    """Inspect the versioned response DB and its complete HAZOP rule join."""
    catalog = hazop_catalog()
    playbooks = load_playbooks()
    return {"version": playbooks["version"], "sources": playbooks["sources"],
            "common_response": playbooks["common_response"], "plans": playbooks["plans"],
            "rule_mappings": [{"rule_id": rule["rule_id"], "node_id": rule["node_id"],
                               "sensor_id": rule["sensor_id"], "scenario": rule["시나리오명"],
                               "response_plan_id": rule.get("대응유형") or classify_rule(rule),
                               "response_stages": rule.get("비상대응_단계") or {},
                               "source_ids": rule.get("대응근거_출처") or []}
                              for rule in catalog["rules"]]}


def _sensor_analysis_context(job_id: str, sensor_id: str,
                             time_s: float | None = None) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Snapshot one sensor and its linked rules without holding the job lock during SAGA I/O."""
    with _jobs_lock:
        job = _jobs.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Simulation not found")
        if not job["frames"]:
            raise HTTPException(status_code=409, detail="No sensor frame available yet")
        latest = job["frames"][-1]
        if time_s is None:
            selected = latest
        else:
            selected = min(job["frames"], key=lambda item: abs(item["time_s"] - time_s))
            if abs(selected["time_s"] - time_s) > max(0.001, abs(time_s) * 1e-8):
                raise HTTPException(status_code=409, detail="Displayed sensor frame is no longer retained")
        frame = dict(selected)
        detail = dict(job.get("hazop_detail") or {}) if selected is latest else {}
    catalog = load_catalog()
    sensor = next((item for item in catalog["sensors"] if item["sensor_id"] == sensor_id), None)
    if sensor is None:
        raise HTTPException(status_code=404, detail="Sensor not found")
    node = next((item for item in catalog["nodes"] if item["node_id"] == sensor["node_id"]), {})
    mapping = next((item for item in catalog["mappings"] if item["sensor_id"] == sensor_id), {})
    related_nodes = {sensor["node_id"]}
    if sensor["node_id"] in {"N07", "N08", "N09"}:
        related_nodes.add("N22")  # Storage boundary gas head covers the bank row.
    elif sensor["node_id"] == "N22":
        related_nodes.update({"N07", "N08", "N09"})
    hazop = frame.get("hazop") or {}
    signals = hazop.get("signals") or {}
    current_rules = {item.get("rule_id"): item for item in detail.get("rules") or hazop.get("active") or []
                     if isinstance(item, dict)}
    playbooks = load_playbooks()
    plans = {plan["id"]: plan for plan in playbooks["plans"]}
    rules = []
    for rule in catalog["rules"]:
        if rule["sensor_id"] != sensor_id:
            continue
        result = current_rules.get(rule["rule_id"], {})
        rules.append({"rule_id": rule["rule_id"], "sensor_id": sensor_id,
                      "scenario": rule["시나리오명"],
                      "expression": rule["신호식"], "operator": rule["연산자"],
                      "threshold": rule["임계값"], "unit": rule["단위"],
                      "severity": rule["등급"], "persistence_s": rule["지속_s"],
                      "cause": rule["원인후보"], "progression": rule["사고_전개조건"],
                      "diagnostic_limit": rule["진단한계"],
                      "response_plan_id": classify_rule(rule),
                      "response_guidance": rule.get("비상대응_단계") or {},
                      "response_source_ids": rule.get("대응근거_출처") or [],
                      "active": bool(result.get("active")), "state": result.get("state") or "PENDING_DATA",
                      "condition_status": result.get("condition_status"),
                      "evaluated_value": result.get("value"), "quality": result.get("quality")})
    plan_ids = dict.fromkeys(rule["response_plan_id"] for rule in rules)
    node_signals = {tag: {"value": value.get("value"), "unit": value.get("unit"),
                          "quality": value.get("quality")}
                    for tag, value in signals.items() if isinstance(value, dict)
                    and any(s["node_id"] in related_nodes and s["sensor_id"] == tag
                            for s in catalog["sensors"])}
    releases = [item for item in hazop.get("releases") or [] if isinstance(item, dict)
                and item.get("component_id") == node.get("누출_target")]
    release_flow_g_s = sum(max(0.0, float(item.get("mass_flow_g_s") or 0.0)) for item in releases)
    physical_leak_g_s = sum(max(0.0, float(item.get("mass_flow_g_s") or 0.0)) for item in releases
                               if not str(item.get("release_id") or "").startswith("relief-"))
    relief_discharge_g_s = release_flow_g_s - physical_leak_g_s
    gas_signal = None
    if sensor_id.startswith("GD-") and isinstance(signal := signals.get(sensor_id), dict):
        thresholds = [float(rule["임계값"]) for rule in catalog["rules"] if rule["sensor_id"] == sensor_id]
        value = signal.get("value")
        if isinstance(value, (int, float)) and signal.get("quality") == "GOOD":
            gas_signal = {"value_volpct_h2": float(value),
                          "alarm_threshold_volpct_h2": min(thresholds) if thresholds else None,
                          "hydrogen_observed": float(value) > 0.0,
                          "alarm_threshold_exceeded": bool(thresholds and float(value) >= min(thresholds))}
    catalog_rules = {rule["rule_id"]: rule for rule in catalog["rules"]}
    related_active = []
    for item in hazop.get("active") or []:
        if not isinstance(item, dict) or item.get("node_id") not in related_nodes or item.get("sensor_id") == sensor_id:
            continue
        definition = catalog_rules.get(item.get("rule_id"))
        if definition is not None:
            plan_id = classify_rule(definition)
            plan_ids[plan_id] = None
            related_active.append({**item, "scenario": definition["시나리오명"],
                                   "response_plan_id": plan_id,
                                   "expression": definition["신호식"],
                                   "operator": definition["연산자"],
                                   "threshold": definition["임계값"],
                                   "unit": definition["단위"],
                                   "persistence_s": definition["지속_s"],
                                   "cause": definition["원인후보"],
                                   "progression": definition["사고_전개조건"],
                                   "diagnostic_limit": definition["진단한계"],
                                   "evaluated_value": item.get("value"),
                                   "response_guidance": definition.get("비상대응_단계") or {},
                                   "response_source_ids": definition.get("대응근거_출처") or []})
    signal = signals.get(sensor_id)
    signal_issue = isinstance(signal, dict) and signal.get("quality") in {"BAD", "STALE", "FAULT", "INVALID"}
    if signal_issue:
        plan_ids["sensor_fault"] = None
    active_rule_count = sum(bool(rule["active"]) for rule in rules)
    payload = {"time_s": frame.get("time_s"), "sensor": sensor, "node": node,
               "mapping": mapping, "signal": signal, "rules": rules,
               "response_plans": {plan_id: plans[plan_id] for plan_id in plan_ids},
               "response_sources": {key: playbooks["sources"][key]
                                    for plan_id in plan_ids for key in plans[plan_id]["sources"]},
               "related_signals": node_signals, "related_active_rules": related_active,
               "related_active_count": len(related_active),
               "active_rule_count": active_rule_count,
               "sensor_status": "ALERT" if active_rule_count else "SIGNAL_ISSUE" if signal_issue else "NORMAL",
               "releases": releases,
               "gas_signal_evidence": gas_signal,
               "simulated_release_evidence": {"active": release_flow_g_s > 0.001,
                                              "mass_flow_g_s": release_flow_g_s,
                                              "physical_leak_g_s": physical_leak_g_s,
                                              "relief_discharge_g_s": relief_discharge_g_s,
                                              "release_ids": [item.get("release_id") for item in releases]},
               "station_status": (frame.get("analysis") or _analyze_frame(frame)).get("status", "NORMAL")}
    return payload, frame, catalog


@app.get("/api/simulations/{job_id}/sensors/{sensor_id}")
def simulation_sensor_detail(job_id: str, sensor_id: str, time_s: float | None = None) -> dict[str, Any]:
    payload, _, _ = _sensor_analysis_context(job_id, sensor_id, time_s)
    return payload


@app.post("/api/simulations/{job_id}/sensors/{sensor_id}/analyze")
async def analyze_simulation_sensor(job_id: str, sensor_id: str,
                                    request: SensorAnalysisInput) -> dict[str, Any]:
    payload, frame, catalog = _sensor_analysis_context(job_id, sensor_id, request.time_s)
    active_rules = [rule for rule in payload["rules"] if rule["active"]]
    related_rules = payload["related_active_rules"]
    alert = payload["sensor_status"] == "ALERT"
    impact_results: list[dict[str, Any]] = []
    current_triggers = [rule for rule in active_rules + related_rules if rule.get("state") == "TRIGGER"]
    if current_triggers:
        backend = await asyncio.to_thread(load_hyram_backend)
        assessed = await asyncio.to_thread(assess_sensor_cases, frame, catalog, backend,
                                           [payload["sensor"]["node_id"]])
        impact_results = [item for item in assessed if item.get("calculation_status") == "calculated"][:2]
    applicable_plan_ids = dict.fromkeys(rule["response_plan_id"] for rule in active_rules)
    applicable_plan_ids.update(dict.fromkeys(rule["response_plan_id"] for rule in related_rules))
    if payload["sensor_status"] == "SIGNAL_ISSUE":
        applicable_plan_ids["sensor_fault"] = None
    if not alert and not related_rules:
        applicable_plan_ids = (dict.fromkeys(["sensor_fault"]) if payload["sensor_status"] == "SIGNAL_ISSUE"
                               else dict.fromkeys(rule["response_plan_id"] for rule in payload["rules"]))
    plans = load_playbooks()
    known_plans = {plan["id"]: plan for plan in plans["plans"]}
    plan_context = []
    for plan_id in applicable_plan_ids:
        plan = known_plans.get(plan_id)
        if plan is None:
            continue
        linked = active_rules + related_rules if alert or related_rules else payload["rules"]
        item = {"situation": plan["title"], "linked_scenarios": [rule["scenario"] for rule in linked
                if rule["response_plan_id"] == plan_id]}
        if alert or any(rule.get("state") == "TRIGGER" for rule in related_rules):
            item.update({key: plan[key] for key in ("recognition", "immediate", "stabilize", "restart", "prevention")})
        else:
            item["prevention"] = plan["prevention"]
            if payload["sensor_status"] == "SIGNAL_ISSUE":
                item["recognition"] = plan["recognition"]
        plan_context.append(item)
    if request.direct:
        # Scope the direct evaluation to the selected equipment. The detailed
        # rules and staged plans are already returned by the sensor detail API.
        focused_frame = {**frame, "hazop": {**(frame.get("hazop") or {}),
                         "signals": payload["related_signals"]}}
        direct_result = await asyncio.to_thread(
            _invoke_saga_hazop_direct, focused_frame, catalog, str(job_id),
            request.question or f"{sensor_id} 현재 상태", impact_results,
        )
        signal = payload["signal"]
        value = signal.get("value")
        unit = signal.get("unit") or ""
        label = payload["node"].get("설비_라인") or payload["sensor"].get("설치_측정위치") or sensor_id
        lines = [f"### {label} · {sensor_id}",
                 f"현재값 **{value:g} {unit}** · 신호 품질 {signal.get('quality', 'UNKNOWN')}"
                 if isinstance(value, (int, float)) else f"현재 신호 품질 {signal.get('quality', 'UNKNOWN')}"]
        current_rules = [rule for rule in active_rules + related_rules if rule.get("state") == "TRIGGER"]
        if current_rules:
            names = list(dict.fromkeys(str(rule.get("scenario") or "이상 징후") for rule in current_rules))
            lines.append("**현재 주의·경보:** " + ", ".join(names[:4]))
        elif active_rules or related_rules:
            lines.append("**경보 이력 유지:** 현재값과 과거 경보 유지 상태를 구분해 확인합니다.")
        elif payload["sensor_status"] == "SIGNAL_ISSUE":
            lines.append("**계측 신호 이상:** 현장 계측 상태를 확인합니다.")
        else:
            lines.append("현재 선택 센서는 정상 범위입니다.")
        gas = payload.get("gas_signal_evidence") or {}
        if gas.get("hydrogen_observed"):
            lines.append(f"수소 농도 **{gas['value_volpct_h2']:.3f} vol%** 관측"
                         + (" · 경보 기준 초과" if gas.get("alarm_threshold_exceeded") else " · 경보 기준 미만"))
        release = payload.get("simulated_release_evidence") or {}
        if release.get("physical_leak_g_s", 0) > 0.001:
            lines.append(f"현재 모의 공정 누출 **{release['physical_leak_g_s']:.3f} g/s**")
        if release.get("relief_discharge_g_s", 0) > 0.001:
            lines.append(f"현재 안전밸브 방출 **{release['relief_discharge_g_s']:.3f} g/s**")
        direct_answer = _safe_saga_text(_direct_hazop_answer(direct_result)) if direct_result else ""
        if current_rules and re.search(r"(?:정상\s*운전|정상\s*범위|이상\s*없|경보\s*없)", direct_answer):
            direct_answer = ""
        if direct_answer and (current_rules or payload["sensor_status"] == "NORMAL"):
            lines.append(direct_answer)
        impact_text = _direct_impact_summary(impact_results)
        if impact_text:
            lines.append(impact_text)
        if current_rules:
            actions = list(dict.fromkeys(str(action) for plan in plan_context
                for action in (plan.get("immediate") or []) if action))[:3]
            if actions:
                lines.append("**우선 대응**\n" + "\n".join(f"- {action}" for action in actions))
        else:
            prevention = list(dict.fromkeys(str(action) for plan in plan_context
                for action in (plan.get("prevention") or []) if action))[:2]
            if prevention:
                lines.append("**안전관리**\n" + "\n".join(f"- {action}" for action in prevention))
        return {"sensor_id": sensor_id, "time_s": payload["time_s"],
                "answer": "\n\n".join(lines), "model": "SAGA 직답 · 센서 기반 계산",
                "impact_results": impact_results,
                "active_rule_count": len(active_rules), "related_active_count": len(related_rules),
                "sensor_status": payload["sensor_status"], "hazop_direct": direct_result}
    scenario_guidance = [{"rule_id": rule["rule_id"], "scenario": rule["scenario"],
                          "sensor_id": rule["sensor_id"] if "sensor_id" in rule else sensor_id,
                          "trigger": f"{rule.get('expression', rule.get('sensor_id', sensor_id))} {rule.get('operator', '')} {rule.get('threshold', '')} {rule.get('unit', '')}",
                          "stages": {stage: (rule.get("response_guidance") or {}).get(stage, [])[:count]
                                     for stage, count in (("recognition", 1), ("immediate", 2),
                                                          ("stabilize", 1), ("restart", 1), ("prevention", 1))}}
                         for rule in active_rules + related_rules] if alert or related_rules else []
    compact_rules = lambda rows: [{key: rule.get(key) for key in
                                   ("rule_id", "sensor_id", "scenario", "state", "condition_status",
                                    "severity", "evaluated_value", "threshold", "unit", "quality", "cause")
                                   if rule.get(key) is not None} for rule in rows]
    gas_thresholds = {item["sensor_id"]: min(float(rule["임계값"]) for rule in catalog["rules"]
                                                    if rule["sensor_id"] == item["sensor_id"])
                      for item in catalog["sensors"] if item["sensor_id"].startswith("GD-")
                      and any(rule["sensor_id"] == item["sensor_id"] for rule in catalog["rules"])}
    current_gas_alerts = [{"tag": tag, "value": signal["value"], "threshold": gas_thresholds[tag]}
                          for tag, signal in payload["related_signals"].items()
                          if tag in gas_thresholds and signal.get("quality") == "GOOD"
                          and isinstance(signal.get("value"), (int, float))
                          and signal["value"] >= gas_thresholds[tag]]
    observed_gas = [{"tag": tag, "value_volpct_h2": signal["value"],
                     "alarm_threshold_volpct_h2": gas_thresholds.get(tag)}
                    for tag, signal in payload["related_signals"].items()
                    if tag.startswith("GD-") and signal.get("quality") == "GOOD"
                    and isinstance(signal.get("value"), (int, float)) and signal["value"] > 0.0]
    retained_gas_alerts = sorted({rule["sensor_id"] for rule in active_rules + related_rules
                                  if rule.get("sensor_id", "").startswith("GD-")
                                  and rule.get("state") in {"LATCHED", "ALARM_HOLD"}})
    context = {"time_s": payload["time_s"], "sensor": {
        "tag": sensor_id, "type": payload["sensor"].get("종류"),
        "location": payload["sensor"].get("설치_측정위치"), "node": payload["node"].get("설비_라인"),
        "current": payload["signal"], "mapping": payload["mapping"]},
        "sensor_status": payload["sensor_status"], "impact_results": impact_results,
        "detection_summary": {"observed_hydrogen_readings": observed_gas,
                              "current_gas_alerts": current_gas_alerts,
                              "retained_gas_alarm_tags": retained_gas_alerts},
        "selected_gas_signal_evidence": payload["gas_signal_evidence"],
        "simulated_release_evidence": payload["simulated_release_evidence"],
        "active_scenarios": compact_rules(active_rules),
        "same_equipment_active_signals": compact_rules(related_rules),
        "related_signals": payload["related_signals"],
        "scenario_specific_guidance": scenario_guidance,
        "monitored_scenarios": [{"scenario": rule["scenario"], "sensor_id": sensor_id,
                                  "threshold": rule["threshold"], "unit": rule["unit"],
                                  "state": rule["state"]} for rule in payload["rules"]],
        "active_faults": frame.get("active_faults") or [],
        "fire_detection": (frame.get("analysis") or {}).get("fire_detection"),
        "relief_valves_open": (frame.get("relief_valves_open") or []) if alert else [],
        "actual_releases": payload["releases"],
        "applicable_guidance": [{"situation": plan["situation"],
                                 "prevention": (plan.get("prevention") or [])[:2]}
                                for plan in plan_context] if not alert else [],
        "station_status": payload["station_status"]}
    if alert:
        retained_only = not any(rule.get("state") == "TRIGGER" for rule in active_rules)
        status_instruction = (("선택 센서의 경보 임계값은 현재 재초과되지 않았고 이전 경보가 유지 중입니다. 현재 경보와 경보 이력을 구분하되, 비영점 가스 농도나 모의 누출을 부정하지 마세요. "
                               if retained_only else "선택 센서에서 동시에 활성화된 모든 시나리오를 각각 검토하고, 공통 원인·상호 악화 가능성·대응 우선순위를 종합하세요. ") +
                              "한 시나리오만 활성이라도 제공된 원인 후보와 연동 신호로 복수의 가능한 전개 경로를 비교하되, 확인되지 않은 경로를 발생 사고로 단정하지 마세요. "
                              "활성 시나리오와 아직 기준에 도달하지 않은 감시 시나리오를 명확히 구분하세요. ")
    elif payload["sensor_status"] == "SIGNAL_ISSUE":
        status_instruction = ("선택 센서의 신호 품질에 이상이 있습니다. 공정 사고를 단정하거나 비상대응을 출력하지 말고 "
                              "계측 검증과 안전한 운전 판단, 예방·안전관리만 설명하세요. ")
    elif related_rules:
        status_instruction = ("선택 센서 자체와 관련 구역의 다른 센서를 분리해 설명하세요. "
                              "선택 센서가 정상이어도 관련 센서의 활성 경보 또는 래치 이력을 빠뜨리지 마세요. "
                              "현재 검지값이 경보 기준 미만이고 상태가 LATCHED/ALARM_HOLD라면 과거 경보 조건의 유지 이력으로 설명하세요. 현재 비영점 농도 관측 여부는 별도로 설명하세요. ")
    else:
        status_instruction = ("선택 센서는 정상입니다. 현재 사고나 비상대응을 출력하지 말고, "
                              "여러 감시 시나리오의 기준과 예방·안전관리만 요약하세요. ")
    prompt = ("당신은 H70 수소충전소의 선택 센서 분석 보조자입니다. 이 데이터는 실제 현장 계측이 아닌 시뮬레이션입니다. "
        "외부 화재 시나리오 입력을 화염검지 확인으로 표현하지 마세요. FD 신호는 모의 위치·응답지연으로 계산된 가상 검지이며 독립적인 현장 실측이 아닙니다. "
        "선택 센서의 현재 상태와 같은 설비·인접 저장구역의 관련 신호를 함께 분석하세요. "
        "연결 규칙의 현재 판정과 임계값, 신호 품질을 구분하고 원인·사고 전개는 가능성으로만 표현하세요. "
        "observed_hydrogen_readings는 현재 양의 수소 농도 관측, current_gas_alerts는 경보 임계값 초과, retained_gas_alarm_tags는 과거 경보 유지입니다. "
        "current_gas_alerts가 비어 있어도 수소 농도 관측이나 실제 모의 누출이 없다는 뜻이 아닙니다. 세 상태를 구분하세요. "
        "simulated_release_evidence의 physical_leak_g_s가 양수이면 모의 공정 누출, relief_discharge_g_s가 양수이면 안전밸브 방출이 진행 중입니다. "
        "현재 방출률과 가스 농도를 먼저 명시하고, 진행 중인 누출을 '누출 없음'으로 답하지 마세요. "
        "경보 시 scenario_specific_guidance의 각 시나리오를 따로 분석하고 단계별 조치를 현재 센서와 연결하세요. "
        + status_instruction +
        "실제 누출, 안전밸브 방출, 센서값 기준 가정 누출을 혼동하지 마세요. 계산된 피해영향 수치만 언급하고 안전거리를 확정하지 마세요. "
        "사용자에게 HAZOP·DB·규칙 ID나 계산 엔진 제품명을 노출하지 마세요. "
        + ("한국어 Markdown으로 '현재 상태', '관련 구역의 경보·이력', '예방·안전관리' 순서로 답하세요. "
           if not alert else "한국어 Markdown으로 '현재 판정', '동시 시나리오와 상호 영향', '우선 대응', '지속 관리' 순서로 답하세요. ") +
        ("사용자 질문에 먼저 직접 답하고, 관측값·관련 신호·원인 후보·다음 확인사항을 근거와 함께 상세히 풀어주세요. "
         "서로 다른 내용을 제목, 짧은 표, 번호 목록으로 구분하세요. 핵심 판단과 주의사항은 Markdown 인용문(> **판단** …, > **주의** …)으로 표현하세요. "
         "입력이 뒷받침하지 않는 수치나 상황을 만들지 말고 확정 관측·계산·가정을 구분하세요. 원시 HTML이나 이모지는 쓰지 마세요. "
         if request.question else
         "가장 중요한 현재 상태와 조치를 4~6문장으로 간결하게 답하세요. 상세 절차는 화면에 별도 표시됩니다. ") +
        "추가 계산을 사용자에게 요청하지 마세요.\n"
        f"운전자 추가 질문: {request.question or '현재 센서 상태와 위험 및 대응 우선순위를 분석해줘.'}\n선택 센서 데이터:\n"
        + json.dumps(context, ensure_ascii=False, default=str)[:6000])[:8200]
    try:
        reply = await _invoke_saga_selected(prompt, "detailed" if request.question else "concise",
                                            request.provider, explicit_length=True, stream_output=True)
    except (URLError, HTTPError, TimeoutError, OSError) as exc:
        raise HTTPException(status_code=503, detail=f"SAGA 센서 분석 실패: {exc}") from exc
    answer = _safe_saga_text(str(reply.get("answer") or ""))
    gas_evidence = payload["gas_signal_evidence"] or {}
    release_evidence = payload["simulated_release_evidence"]
    evidence_lines = []
    if gas_evidence.get("hydrogen_observed"):
        threshold = gas_evidence.get("alarm_threshold_volpct_h2")
        alarm_note = (f"경보 기준 {threshold:g} vol% {'초과' if gas_evidence['alarm_threshold_exceeded'] else '미만'}"
                      if threshold is not None else "경보 기준 미연결")
        evidence_lines.append(f"{sensor_id} 수소 농도 {gas_evidence['value_volpct_h2']:.3f} vol% H₂ 관측 ({alarm_note})")
    if release_evidence["physical_leak_g_s"] > 0.001:
        evidence_lines.append(f"모의 공정 누출 {release_evidence['physical_leak_g_s']:.3f} g/s 진행 중")
    if release_evidence["relief_discharge_g_s"] > 0.001:
        evidence_lines.append(f"안전밸브 방출 {release_evidence['relief_discharge_g_s']:.3f} g/s 진행 중")
    if evidence_lines:
        conflicting_release = release_evidence["physical_leak_g_s"] > 0.001 and re.search(
            r"(?:누출|방출)(?:이|은|은 현재|은 실제)?\s*(?:없|미발생|발생하지|확인되지|관찰되지)", answer)
        conflicting_gas = gas_evidence.get("hydrogen_observed") and re.search(
            r"(?:가스|수소).{0,30}(?:감지|검출|관측).{0,70}(?:없|되지 않|미확인)", answer)
        if conflicting_release or conflicting_gas:
            answer = "현재 확인된 모의 신호를 기준으로 누출 위치와 주변 설비를 확인하고, 가운데 표시된 단계별 대응을 적용하세요."
        answer = "**현재 확인된 신호** · " + " · ".join(evidence_lines) + "\n\n" + answer
    return {"sensor_id": sensor_id, "time_s": payload["time_s"],
            "answer": answer or "선택 센서의 상태를 확인했습니다.",
            "model": reply.get("model", ""), "impact_results": impact_results,
            "active_rule_count": len(active_rules), "related_active_count": len(related_rules),
            "sensor_status": payload["sensor_status"]}


@app.post("/api/simulations/{job_id}/sensors/{sensor_id}/analyze/stream")
async def analyze_simulation_sensor_stream(job_id: str, sensor_id: str,
                                           request: SensorAnalysisInput) -> StreamingResponse:
    return _stream_analysis_response(
        lambda: analyze_simulation_sensor(job_id, sensor_id, request),
        "선택 센서와 관련 설비 신호를 분석하고 있습니다…",
    )


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
