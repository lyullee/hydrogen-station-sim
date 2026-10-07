"""FastAPI service for hydrogen-station simulation and monitoring."""

from __future__ import annotations

import asyncio
from contextvars import ContextVar
from copy import deepcopy
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
from .llm_grounding import (
    build_evidence_manifest,
    guard_llm_claims,
    prompt_decision_evidence,
)
from .safe_operation import SafeOperationSample
from .simulation_clock import SimulationClock
from .virtual_safety import VALVE_LABELS, ZONES, RECOVERY_CHECKS, suggested_actions
from .scenario import ReferenceScenario, build_reference_scenario
from .calibration_profiles import (
    load_bank_pressure_envelopes,
    load_measured_boundary_calibration,
    load_station_recharge_dynamics_calibration,
)
from .dispersion_proxy import PUBLIC_DISPERSION_PROXY
from .public_benchmarks import compare_public_operating_context
from .safety_runtime import FaultEvent, FaultKind, FaultSchedule
from .tabulated import PropsSI
from .hazop.database import EventStore, load_catalog
from .hazop.mapping import coverage as hazop_coverage
from .hazop.runtime import HazopMonitor
from .hazop.response import (classify_rule, load_playbooks, response_selection,
                             prompt_guidance, render_guidance, structured_guidance)


def _runtime_calibration_payload(
    profile: Any | None,
    recharge_dynamics_profile: Any | None = None,
    *,
    recharge_dynamics_requested: bool = False,
) -> dict[str, Any]:
    """Serialize sanitized calibration provenance for jobs and operator views."""

    result = (
        {"id": "reference_defaults", "evidence_artifact": None}
        if profile is None else profile.runtime_metadata()
    )
    result["station_recharge_dynamics"] = (
        recharge_dynamics_profile.runtime_metadata()
        if recharge_dynamics_profile is not None else {
            "status": "unavailable" if recharge_dynamics_requested else "disabled",
            "id": None,
            "evidence_artifact": None,
            "claim_boundary": (
                "Only an owner-attested, temporally checked station-side restart "
                "dwell may be applied; reference defaults remain unchanged."
            ),
        }
    )
    return result


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
    ignited: bool = False
    enclosure_volume_m3: float | None = Field(default=None, gt=0.0, le=1.0e6)
    enclosure_vent_area_m2: float | None = Field(default=None, gt=0.0, le=1.0e4)
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
            ignited=self.ignited,
            enclosure_volume_m3=self.enclosure_volume_m3,
            enclosure_vent_area_m2=self.enclosure_vent_area_m2,
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
    recharge_restart_margin_low_mpa: float = Field(default=2.0, ge=0.2, le=20.0)
    recharge_restart_margin_medium_mpa: float = Field(default=3.0, ge=0.2, le=20.0)
    # Eight de-identified station-side traces show a 4.555 MPa median
    # stop-to-restart drop across 124 completed high-stage restarts. The
    # rounded 4.5 MPa development default reduces rapid restart cycling; it is
    # a controller-behavior setting, not a safety limit or full-loop validation.
    recharge_restart_margin_high_mpa: float = Field(default=4.5, ge=0.2, le=20.0)
    risk_overlay_enabled: bool = True
    risk_display_mode: Literal["relative", "absolute"] = "relative"
    risk_update_interval_s: Literal[15, 30, 60, 120] = 30
    measured_boundary_calibration: bool = False
    # A measured restart dwell may be applied only after a multi-trace
    # chronological holdout passes.  The current evidence does not pass that
    # gate, so reference behaviour is the safe default and the loader rejects
    # the superseded single-trace profile.
    measured_station_dynamics_calibration: bool = False
    vehicle_1_auto_stop: bool = True
    vehicle_1_target_pressure_mpa: float = Field(default=70.0, gt=1.0, le=110.0)
    vehicle_2_auto_stop: bool = True
    vehicle_2_target_pressure_mpa: float = Field(default=70.0, gt=1.0, le=110.0)
    relief_valves: dict[str, ReliefValveInput] = Field(default_factory=_default_relief_valves)

    @model_validator(mode="after")
    def valid_relief_targets(self):
        if set(self.relief_valves) != set(RELIEF_TARGETS):
            raise ValueError("Settings are required for every relief valve")
        for name in ("low", "medium", "high"):
            if getattr(self, f"recharge_restart_margin_{name}_mpa") >= getattr(self, f"recharge_target_{name}_mpa"):
                raise ValueError(f"{name} recharge restart margin must be below the target pressure")
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
    # Optional public-capacity geometry.  The default keeps the historical
    # reference volume; capacity_eos uses the tabulated hydrogen EOS.
    vehicle_geometry_basis: Literal["reference", "capacity_eos"] = "reference"
    vehicle_tank_calibration: Literal["public_type_iv", "reference"] = "public_type_iv"
    vehicle_capacity_kg: float | None = Field(default=None, gt=0.1, le=100.0)
    initial_vehicle_2_pressure_mpa: float = Field(default=8.0, gt=0.0, le=70.0)
    initial_vehicle_2_temperature_c: float = Field(default=25.0, ge=-40.0, le=85.0)
    vehicle_2_capacity_kg: float | None = Field(default=None, gt=0.1, le=100.0)
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
        if self.vehicle_geometry_basis == "capacity_eos" and (
            self.vehicle_capacity_kg is None or self.vehicle_2_capacity_kg is None
        ):
            raise ValueError(
                "capacity_eos geometry requires vehicle_capacity_kg and "
                "vehicle_2_capacity_kg"
            )
        return self


class SagaChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=1200)


class SimulationSpeedInput(BaseModel):
    speed_multiplier: Literal[0.5, 1, 2, 3, 5, 10, 30, 50, 100]


class VirtualSafetyActionInput(BaseModel):
    kind: Literal["valve.close", "valve.open", "vent.close", "vent.open",
                  "operation.stop", "esd.trip", "ventilation.on", "ventilation.off",
                  "cooling.on", "cooling.off", "power.isolate", "power.restore",
                  "access.restrict", "access.release", "personnel.evacuate", "vehicle.evacuate",
                  "responders.notify", "recovery.record", "repair.leak", "purge.run",
                  "tightness.test", "detector.test", "valve.test", "pressure.test",
                  "restart.approve"]
    target: str
    note: str = Field(default="", max_length=240)


class VirtualDeviceFaultInput(BaseModel):
    fault: Literal["none", "stuck_open", "stuck_closed", "seat_leak", "feedback_fault", "failure"]


class VirtualEnvironmentInput(BaseModel):
    wind_direction_deg: float = Field(ge=0, lt=360)
    wind_speed_m_s: float = Field(ge=0, le=40)


class VirtualTrainingCompareInput(BaseModel):
    other_job_id: str


class SagaAnalysisInput(BaseModel):
    provider: Literal["service_hub", "groq"] = "service_hub"
    language: Literal["ko", "en"] = "ko"
    question: str = Field(default="현재 공정의 이상 징후와 조치 우선순위를 분석해 주세요.", max_length=1200)
    trigger: str = Field(default="manual", pattern="^(manual|periodic|alarm)$")
    scenario_mode: bool = False
    # The monitor uses the dedicated /direct route; the legacy analysis route
    # retains its request contract for existing integrations.
    direct: bool = False
    one_pass: bool = False
    history: list[SagaChatTurn] = Field(default_factory=list, max_length=8)


class SensorAnalysisInput(BaseModel):
    provider: Literal["service_hub", "groq"] = "service_hub"
    language: Literal["ko", "en"] = "ko"
    question: str = Field(default="", max_length=1200)
    time_s: float | None = Field(default=None, ge=0)
    direct: bool = False
    one_pass: bool = False


class MainAssistantInput(BaseModel):
    """Public contract for the main monitor assistant only."""

    provider: Literal["service_hub", "groq"] = "service_hub"
    language: Literal["ko", "en"] = "ko"
    question: str = Field(min_length=1, max_length=1200)
    trigger: Literal["manual", "periodic", "alarm"] = "manual"
    scenario_mode: bool = False
    history: list[SagaChatTurn] = Field(default_factory=list, max_length=8)


class SensorAssistantInput(BaseModel):
    """Public contract for the selected-sensor assistant only."""

    provider: Literal["service_hub", "groq"] = "service_hub"
    language: Literal["ko", "en"] = "ko"
    question: str = Field(default="", max_length=1200)
    time_s: float | None = Field(default=None, ge=0)


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
_risk_zone_cache: dict[str, dict[str, Any]] = {}
_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="h2station")
_saga_token_sink: ContextVar[Callable[[str], None] | None] = ContextVar("saga_token_sink", default=None)

# The main monitor already renders deterministic consequence cards and the
# complete staged response plan below the conversational answer. Bound only
# that generated headline; selected-sensor analysis retains its larger budget.
MAIN_ASSISTANT_MAX_TOKENS = 900


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
        process_settings = request.process_settings
        measured_profile = (
            load_measured_boundary_calibration()
            if process_settings is not None and process_settings.measured_boundary_calibration
            else None
        )
        recharge_dynamics_profile = (
            load_station_recharge_dynamics_calibration()
            if process_settings is not None
            and process_settings.measured_station_dynamics_calibration
            else None
        )
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
            vehicle_geometry_basis=request.vehicle_geometry_basis,
            vehicle_tank_calibration=request.vehicle_tank_calibration,
            vehicle_capacity_kg=request.vehicle_capacity_kg,
            initial_vehicle_2_pressure_pa=(
                request.initial_vehicle_2_pressure_mpa * 1.0e6
            ),
            initial_vehicle_2_temperature_k=(
                request.initial_vehicle_2_temperature_c + 273.15
            ),
            vehicle_2_capacity_kg=request.vehicle_2_capacity_kg,
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
            # The owner-controlled profile is a station-boundary dispatch
            # reference.  Apply it only when the operator explicitly opts in;
            # the default reference model remains unchanged.
            station_dispatch_pressure_margin_pa=(
                measured_profile.recharge_restart_margin_pa
                if measured_profile is not None else None
            ),
            station_recharge_hysteresis_pa=(
                measured_profile.recharge_hysteresis_pa
                if measured_profile is not None else None
            ),
            station_minimum_recharge_off_time_s=(
                recharge_dynamics_profile.minimum_recharge_off_time_s
                if recharge_dynamics_profile is not None else 0.0
            ),
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
                reset_safety = bool(job.pop("pending_safety_reset", False))
                if reset_safety:
                    built.simulator.safety_plc.reset()
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
            calibration_profile=_runtime_calibration_payload(
                measured_profile,
                recharge_dynamics_profile,
                recharge_dynamics_requested=bool(
                    process_settings
                    and process_settings.measured_station_dynamics_calibration
                ),
            ),
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
                        "virtual_detector_proxy": (sample.hazop or {}).get("virtual_detector_proxy"),
                        "bank_pressure_mpa": {
                            name: pressure / 1.0e6
                            for name, pressure in sample.bank_pressure_pa.items()
                        },
                        "bank_temperature_c": {
                            name: temperature - 273.15
                            for name, temperature in (sample.bank_temperature_k or {}).items()
                        },
                        "bank_mass_kg": dict(sample.bank_mass_kg or {}),
                        "header_pressure_mpa": (
                            sample.header_pressure_pa / 1.0e6
                            if sample.header_pressure_pa is not None else None
                        ),
                        "header_temperature_c": (
                            sample.header_temperature_k - 273.15
                            if sample.header_temperature_k is not None else None
                        ),
                        "header_mass_kg": sample.header_mass_kg,
                        "header_inflow_g_s": (
                            sample.header_inflow_kg_s * 1000.0
                            if sample.header_inflow_kg_s is not None else None
                        ),
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
                        "virtual_safety": sample.virtual_safety,
                        "realtime_lag_s": realtime_lag_s,
                        "simulation_rate_x": simulation_rate_x,
                        "vehicle_mass_kg": sample.vehicle_mass_kg,
                        "vehicle_2_mass_kg": sample.vehicle_2_mass_kg,
                        # Preserve the selected geometry basis in every
                        # snapshot so LLM evidence can distinguish the
                        # reference default from the opt-in capacity/EOS
                        # sensitivity path.
                        "vehicle_geometry_basis": request.vehicle_geometry_basis,
                        "vehicle_tank_calibration": request.vehicle_tank_calibration,
                        "vehicle_capacity_kg": request.vehicle_capacity_kg,
                        "vehicle_2_capacity_kg": request.vehicle_2_capacity_kg,
                        "detector_policy": {
                            "source_artifact": built.simulator.safety_plc.limits.detector_policy_source,
                            "source_doi": built.simulator.safety_plc.limits.detector_policy_doi,
                            "source_license": "CC BY 4.0" if built.simulator.safety_plc.limits.detector_policy_status == "PUBLIC_REPLAY_RULE_APPLIED" else "",
                            "status": built.simulator.safety_plc.limits.detector_policy_status,
                            "alarm_threshold_volpct_h2": built.simulator.safety_plc.limits.detector_alarm_volume_fraction * 100.0,
                            "trip_threshold_volpct_h2": built.simulator.safety_plc.limits.detector_trip_volume_fraction * 100.0,
                            "persistence_s": built.simulator.safety_plc.limits.trip_persistence_s,
                            "claim_limit": built.simulator.safety_plc.limits.detector_policy_claim_limit,
                        },
                    }
                if measured_profile is not None:
                    boundary_pressure = (
                        (frame.get("process_operations") or {})
                        .get("trailer_pressure_mpa")
                    )
                    frame["measured_boundary_envelope"] = (
                        measured_profile.pressure_envelope_comparison(
                            boundary_pressure
                        )
                    )
                bank_envelope = load_bank_pressure_envelopes()
                if bank_envelope is not None:
                    frame["measured_bank_pressure_envelope"] = bank_envelope.compare(
                        frame.get("bank_pressure_mpa")
                    )
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
                if process_runtime is not None:
                    process_runtime.safety.observe_hazards(sample.active_faults)
                    process_runtime.safety.record_metrics(sample.time_s, _virtual_safety_metrics(frame))
                    resolved_fault_ids = _queue_incident_resolution(
                        _jobs[job_id], process_runtime, sample.time_s
                    )
                    if resolved_fault_ids:
                        frame["incident_resolution"] = {
                            "status": "ending",
                            "fault_ids": resolved_fault_ids,
                            "reason": "ESD와 즉시 조치 확인",
                        }
                    frame["virtual_safety"] = process_runtime.safety.snapshot(include_actions=False)
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
            "average_flow_g_s": float(
                np.mean(trajectory.nozzle_mass_flow_kg_s[trajectory.nozzle_mass_flow_kg_s > 1.0e-9]) * 1000.0
            ) if np.any(trajectory.nozzle_mass_flow_kg_s > 1.0e-9) else 0.0,
            "released_mass_kg": released_mass,
            "esd_time_s": trajectory.esd_time_s,
            "hyram_available": bool(getattr(backend, "available", False)),
            "hyram_backend": backend.name,
            "active_faults": [fault.model_dump() if hasattr(fault, "model_dump") else asdict(fault) for fault in faults],
            "public_benchmark_diagnostics": compare_public_operating_context(
                duration_s=float(trajectory.time_s[-1]),
                start_pressure_mpa=float(trajectory.vehicle_pressure_pa[0] / 1.0e6),
                end_pressure_mpa=float(trajectory.vehicle_pressure_pa[-1] / 1.0e6),
                average_flow_g_s=float(
                    np.mean(trajectory.nozzle_mass_flow_kg_s[trajectory.nozzle_mass_flow_kg_s > 1.0e-9]) * 1000.0
                ) if np.any(trajectory.nozzle_mass_flow_kg_s > 1.0e-9) else 0.0,
                maximum_flow_g_s=float(np.max(trajectory.nozzle_mass_flow_kg_s) * 1000.0),
            ),
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
            "header_pressure_mpa": (trajectory.header_pressure_pa / 1.0e6).tolist(),
            "header_temperature_c": (trajectory.header_temperature_k - 273.15).tolist(),
            "header_mass_kg": trajectory.header_mass_kg.tolist(),
            "header_inflow_g_s": (trajectory.header_inflow_kg_s * 1000.0).tolist(),
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
        "virtual_detector_proxy": PUBLIC_DISPERSION_PROXY.metadata(),
        "hazop": hazop_status,
    }


@app.get("/api/config/defaults")
def default_config() -> dict[str, Any]:
    return SimulationInput().model_dump()


@app.post("/api/simulations", status_code=202)
def create_simulation(request: SimulationInput) -> dict[str, Any]:
    job_id = uuid4().hex
    runtime_settings = request.process_settings.model_dump() if request.process_settings is not None else None
    measured_profile = (
        load_measured_boundary_calibration()
        if runtime_settings is not None and runtime_settings.get("measured_boundary_calibration")
        else None
    )
    recharge_dynamics_profile = (
        load_station_recharge_dynamics_calibration()
        if runtime_settings is not None
        and runtime_settings.get("measured_station_dynamics_calibration")
        else None
    )
    if measured_profile is not None:
        for bank in ("low", "medium", "high"):
            runtime_settings[f"recharge_restart_margin_{bank}_mpa"] = (
                measured_profile.recharge_restart_margin_pa / 1.0e6
            )
    process_runtime = ProcessRuntime(runtime_settings) if runtime_settings is not None else None
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
            "auto_resolved_fault_ids": [],
            "operations": process_runtime.snapshot() if process_runtime is not None else None,
            "calibration_profile": _runtime_calibration_payload(
                measured_profile,
                recharge_dynamics_profile,
                recharge_dynamics_requested=bool(
                    runtime_settings
                    and runtime_settings.get("measured_station_dynamics_calibration")
                ),
            ),
            "station_dynamics_calibration_applied": recharge_dynamics_profile is not None,
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


_RISK_ZONE_NODES = ("N01", "N06", "N07", "N08", "N09", "N13", "N14", "N17", "N18", "N19")
_RISK_ZONE_COMPONENTS = {
    "N01": "supply", "N06": "compressor", "N07": "cascade.low",
    "N08": "cascade.medium", "N09": "cascade.high", "N13": "dispenser.hose",
    "N14": "vehicle.tank", "N17": "dispenser_2.hose", "N18": "vehicle_2.tank",
    "N19": "cooler",
}
_RISK_DESIGN_PRESSURE_MPA = {
    "N01": 50.0, "N06": 100.0, "N07": 50.0, "N08": 70.0, "N09": 100.0,
    "N13": 90.0, "N14": 87.5, "N17": 90.0, "N18": 87.5, "N19": 90.0,
}


@app.get("/api/simulations/{job_id}/risk-zones")
async def simulation_risk_zones(job_id: str) -> dict[str, Any]:
    """Rate-limited current-state screening risk for the spatial overlay."""
    with _jobs_lock:
        job = _jobs.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Simulation not found")
        frames = job.get("frames") or []
        if not frames:
            return {"time_s": None, "zones": [], "status": "waiting"}
        frame = deepcopy(frames[-1])
        settings = ((job.get("operations") or {}).get("settings") or {})
    interval = int(settings.get("risk_update_interval_s", 30))
    sample_time = float(frame.get("time_s") or 0.0)
    bucket = int(sample_time // max(interval, 1))
    cached = _risk_zone_cache.get(job_id)
    if cached and cached.get("bucket") == bucket:
        return cached["payload"]
    backend = await asyncio.to_thread(load_hyram_backend)
    catalog = load_catalog()
    cases = await asyncio.to_thread(
        assess_sensor_cases, frame, catalog, backend, list(_RISK_ZONE_NODES),
        max_cases=len(_RISK_ZONE_NODES),
    )
    zones = []
    for row in cases:
        node = str(row.get("node_id") or "")
        pressure = max(0.0, float(row.get("current_pressure_mpa") or 0.0))
        temperature = float(row.get("current_temperature_c") or 25.0)
        pressure_fraction = min(1.5, pressure / _RISK_DESIGN_PRESSURE_MPA.get(node, 100.0))
        consequence_score = max(0.0, float(row.get("risk_score") or 0.0))
        # Fixed-reference current-state index. It combines stored-energy
        # margin and the bundled consequence-screening result. It is not an
        # annual fatality probability because release frequency is not known.
        absolute = min(100.0, 8.0 + pressure_fraction * 24.0
                       + min(55.0, consequence_score * .65)
                       + min(13.0, max(0.0, temperature - 45.0) * .25))
        zones.append({
            "node_id": node, "component": _RISK_ZONE_COMPONENTS.get(node, node),
            "name": row.get("node_name"), "absolute_score": round(absolute, 1),
            "pressure_mpa": pressure, "temperature_c": temperature,
            "consequence_score": consequence_score,
            "effect_radius_m": max(
                float(row.get("sampled_effect_radius_m") or 0.0),
                float(row.get("flammable_plume_streamline_distance_m") or 0.0),
            ),
            "flammable_plume_distance_m": row.get("flammable_plume_streamline_distance_m"),
            "calculation_status": row.get("calculation_status"),
        })
    maximum = max((zone["absolute_score"] for zone in zones), default=1.0)
    for zone in zones:
        zone["relative_score"] = round(100.0 * zone["absolute_score"] / maximum, 1)
        score = zone["absolute_score"]
        zone["level"] = ("매우 높음" if score >= 80 else "높음" if score >= 60
                         else "주의" if score >= 35 else "낮음" if score >= 15 else "매우 낮음")
    payload = {"time_s": sample_time, "zones": zones, "status": "calculated",
               "backend_available": bool(getattr(backend, "available", False)),
               "update_interval_s": interval,
               "basis": "현재 압력·온도와 1 mm 가정 누출 피해영향의 고정 기준 지수; 연간 개인위험도 아님"}
    _risk_zone_cache[job_id] = {"bucket": bucket, "payload": payload}
    return payload


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
        settings_dict = settings.model_dump()
        dynamics_requested = bool(settings_dict.get("measured_station_dynamics_calibration"))
        dynamics_applied = bool(job.get("station_dynamics_calibration_applied"))
        if dynamics_requested != dynamics_applied:
            raise HTTPException(
                status_code=409,
                detail=(
                    "Station recharge-dynamics calibration is applied when a "
                    "simulation starts; reset and start a new simulation to change it"
                ),
            )
        measured_profile = (
            load_measured_boundary_calibration()
            if settings_dict.get("measured_boundary_calibration") else None
        )
        if measured_profile is not None:
            for bank in ("low", "medium", "high"):
                settings_dict[f"recharge_restart_margin_{bank}_mpa"] = (
                    measured_profile.recharge_restart_margin_pa / 1.0e6
                )
            job["calibration_profile"] = _runtime_calibration_payload(
                measured_profile,
                load_station_recharge_dynamics_calibration() if dynamics_applied else None,
                recharge_dynamics_requested=dynamics_requested,
            )
        else:
            job["calibration_profile"] = _runtime_calibration_payload(
                None,
                load_station_recharge_dynamics_calibration() if dynamics_applied else None,
                recharge_dynamics_requested=dynamics_requested,
            )
        try:
            runtime.configure(settings_dict)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        job["operations"] = runtime.snapshot()
        job["updated_at"] = _utc_now()
        return job["operations"]


def _virtual_safety_metrics(frame: dict[str, Any] | None) -> dict[str, Any]:
    if not frame:
        return {}
    gas = frame.get("gas_detectors") or {}
    ranges = [max(
                    float((release.get("consequence") or {}).get("sampled_effect_radius_m") or
                          (release.get("consequence") or {}).get("effect_radius_m") or 0.0),
                    float((release.get("consequence") or {}).get("flammable_plume_streamline_distance_m") or 0.0),
                  )
              for release in (frame.get("hazop") or {}).get("releases", [])]
    return {"time_s": frame.get("time_s"),
            "bank_pressure_mpa": dict(frame.get("bank_pressure_mpa") or {}),
            "bank_temperature_c": dict(frame.get("bank_temperature_c") or {}),
            "bank_mass_kg": dict(frame.get("bank_mass_kg") or {}),
            "nozzle_1_flow_g_s": frame.get("nozzle_1_flow_g_s", 0.0),
            "nozzle_2_flow_g_s": frame.get("nozzle_2_flow_g_s", 0.0),
            "compressor_flow_g_s": ((frame.get("process_activity") or {}).get("pressure_recharge") or {}).get("flow_g_s", 0.0),
            "total_leak_flow_g_s": frame.get("total_leak_flow_g_s", 0.0),
            "released_mass_kg": frame.get("released_mass_kg", 0.0),
            "gas_max_volpct_h2": max((float(signal.get("value") or 0.0)
                                      for signal in gas.values()), default=0.0),
            "detectors_good": bool(gas) and all(signal.get("quality") == "GOOD"
                                                for signal in gas.values()),
            "effect_radius_m": max(ranges, default=0.0),
             "esd": bool(frame.get("esd"))}


def _queue_incident_resolution(job: dict[str, Any], runtime: ProcessRuntime,
                               time_s: float) -> list[str]:
    """End active injected incidents after ESD and the confirmed immediate stop.

    This is a virtual-training transition, not a claim that a physical leak or fire
    disappears instantly.  Ending the injected source lets the process, detectors,
    consequence model, 3D scene, and flow diagram all follow the same state change.
    """
    state = runtime.safety.snapshot()
    actions = state.get("actions") or []
    registry: dict[str, FaultEvent] = job.get("fault_registry") or {}
    already_queued = set(job.setdefault("auto_resolved_fault_ids", []))
    active = [event for event in registry.values()
              if event.kind is not FaultKind.EMERGENCY_STOP
              and event.active_at(time_s) and event.event_id not in already_queued]
    if not active or not state.get("esd_requested"):
        return []
    incident_start = min(event.start_time_s for event in active)
    esd_confirmed = any(action.get("kind") == "esd.trip"
                        and action.get("status") == "confirmed"
                        and float(action.get("completed_s") or -1) + 1e-6 >= incident_start
                        for action in actions)
    immediate_stop_confirmed = any(action.get("kind") == "operation.stop"
                                   and action.get("target") == "all"
                                   and action.get("status") == "confirmed"
                                   and float(action.get("completed_s") or -1) + 1e-6 >= incident_start
                                   for action in actions)
    if not (esd_confirmed and immediate_stop_confirmed):
        return []
    resolved = [event.event_id for event in active]
    job["pending_fault_commands"].extend(("remove", event_id) for event_id in resolved)
    job["auto_resolved_fault_ids"] = sorted(already_queued | set(resolved))
    job["activity"] = "ESD·즉시 조치 확인 · 사고 입력 자동 종료 반영 중"
    runtime.safety.record_incident_resolution(resolved, time_s)
    return resolved


@app.get("/api/simulations/{job_id}/safety")
def get_virtual_safety(job_id: str) -> dict[str, Any]:
    with _jobs_lock:
        job = _jobs.get(job_id)
        runtime = _process_runtimes.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Simulation not found")
        if runtime is None:
            raise HTTPException(status_code=409, detail="Operator mode is required")
        frame = job["frames"][-1] if job["frames"] else None
        state = runtime.safety.snapshot()
        state["current_metrics"] = _virtual_safety_metrics(frame)
        releases = ((frame or {}).get("hazop") or {}).get("releases") or []
        state["vent_releases"] = {bank: {"outlet_height_m": 6.0,
            "release_flow_g_s": next((float(item.get("mass_flow_g_s") or 0.0)
                                      for item in releases if item.get("release_id") == f"vent-{bank}"), 0.0),
            "residual_pressure_mpa": state["current_metrics"].get("bank_pressure_mpa", {}).get(bank)}
            for bank in ("low", "medium", "high")}
        state["catalog"] = {"valves": VALVE_LABELS, "zones": ZONES,
                            "recovery_checks": RECOVERY_CHECKS}
        active = ((frame or {}).get("hazop") or {}).get("active") or []
        definitions = {row["rule_id"]: row for row in load_catalog()["rules"]}
        suggested = []
        seen = set()
        for row in active:
            if row.get("state") != "TRIGGER":
                continue
            rule = definitions.get(row.get("rule_id"))
            if rule is None:
                continue
            for action in suggested_actions(classify_rule(rule), row.get("node_id")):
                key = (action["kind"], action["target"])
                if key not in seen:
                    seen.add(key)
                    suggested.append({**action, "scenario": rule["시나리오명"]})
        state["suggested_actions"] = suggested[:16]
        return state


@app.post("/api/simulations/{job_id}/safety/actions")
def issue_virtual_safety_action(job_id: str, request: VirtualSafetyActionInput) -> dict[str, Any]:
    with _jobs_lock:
        job = _jobs.get(job_id)
        runtime = _process_runtimes.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Simulation not found")
        if runtime is None or job["status"] not in ("queued", "running"):
            raise HTTPException(status_code=409, detail="Running operator simulation required")
        frame = job["frames"][-1] if job["frames"] else None
        if request.kind == "repair.leak":
            fault = job["fault_registry"].get(request.target)
            if fault is None or fault.kind is not FaultKind.HYDROGEN_LEAK or not fault.active_at(
                max(float(job.get("last_sample_time_s") or 0), runtime.safety.latest_time_s)):
                raise HTTPException(status_code=422, detail="Select an active virtual leak")
        if request.kind == "recovery.record" and frame:
            active_hazards = [fault for fault in frame.get("active_faults") or []
                              if not fault.startswith("relief-open:")]
            if request.target in ("source_removed", "tightness_test", "supervisor_approval") and (
                active_hazards or frame.get("total_leak_flow_g_s", 0) > .01):
                raise HTTPException(status_code=409, detail="Active hazard blocks this recovery check")
            if request.target == "source_removed" and runtime.any_requested():
                raise HTTPException(status_code=409, detail="Stop all process operations before source-removal confirmation")
            if request.target == "leak_repaired" and any(
                fault.kind is FaultKind.HYDROGEN_LEAK for fault in job["fault_registry"].values()):
                raise HTTPException(status_code=409, detail="Repair and remove the simulated leak before recording this check")
            if request.target == "detector_test" and any(
                item.get("quality") != "GOOD" for item in (frame.get("gas_detectors") or {}).values()):
                raise HTTPException(status_code=409, detail="Gas detector quality check failed")
            if request.target == "detector_test" and not frame.get("gas_detectors"):
                raise HTTPException(status_code=409, detail="No gas detector telemetry to test")
            if request.target == "valve_test" and any(
                valve.status == "failed" or valve.feedback_open != valve.actual_open or
                (not valve.commanded_open and valve.flow_fraction() > 0)
                for valve in runtime.safety.valves.values()):
                raise HTTPException(status_code=409, detail="Virtual valve feedback test failed")
        if request.kind == "restart.approve" and frame and (
            frame.get("total_leak_flow_g_s", 0.0) > .01 or
            any(fault.startswith(("external-fire:", "hydrogen-leak:"))
                for fault in frame.get("active_faults") or []) or
            max((float(item.get("value") or 0) for item in (frame.get("gas_detectors") or {}).values()), default=0) >= .2):
            raise HTTPException(status_code=409, detail="Active hazard or gas signal blocks restart")
        now = max(float(job.get("last_sample_time_s") or 0.0), runtime.safety.latest_time_s)
        try:
            action = runtime.safety.issue(request.kind, request.target, now,
                                          process=runtime, note=request.note,
                                          baseline_metrics=_virtual_safety_metrics(frame))
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        if request.kind == "repair.leak":
            job["pending_fault_commands"].append(("remove", request.target))
        if request.kind == "restart.approve":
            job["pending_safety_reset"] = True
        job["updated_at"] = _utc_now()
        return {"action": action, "state": runtime.safety.snapshot()}


@app.put("/api/simulations/{job_id}/safety/faults/{device:path}")
def set_virtual_device_fault(job_id: str, device: str, request: VirtualDeviceFaultInput) -> dict[str, Any]:
    with _jobs_lock:
        job = _jobs.get(job_id)
        runtime = _process_runtimes.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Simulation not found")
        if runtime is None or job["status"] not in ("queued", "running"):
            raise HTTPException(status_code=409, detail="Running operator simulation required")
        try:
            event = runtime.safety.set_fault(device, request.fault,
                                            max(float(job.get("last_sample_time_s") or 0), runtime.safety.latest_time_s))
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return {"event": event, "state": runtime.safety.snapshot()}


@app.put("/api/simulations/{job_id}/safety/environment")
def set_virtual_environment(job_id: str, request: VirtualEnvironmentInput) -> dict[str, Any]:
    with _jobs_lock:
        job = _jobs.get(job_id)
        runtime = _process_runtimes.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Simulation not found")
        if runtime is None or job["status"] not in ("queued", "running"):
            raise HTTPException(status_code=409, detail="Running operator simulation required")
        runtime.safety.wind_direction_deg = request.wind_direction_deg
        runtime.safety.wind_speed_m_s = request.wind_speed_m_s
        return runtime.safety.snapshot()


@app.get("/api/simulations/{job_id}/safety/replay")
def virtual_safety_replay(job_id: str) -> dict[str, Any]:
    with _jobs_lock:
        job = _jobs.get(job_id)
        runtime = _process_runtimes.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Simulation not found")
        if runtime is None:
            raise HTTPException(status_code=409, detail="Operator mode is required")
        return {"job_id": job_id, "actions": deepcopy(runtime.safety.actions),
                "evaluation": _virtual_training_evaluation(job, runtime.safety),
                "frames": [{"time_s": frame["time_s"], "sequence": frame["sequence"],
                            "metrics": _virtual_safety_metrics(frame)} for frame in job["frames"]]}


def _virtual_training_evaluation(job: dict[str, Any], safety) -> dict[str, Any]:
    frames = job["frames"]
    actions = safety.actions
    incident = next((frame for frame in frames if any(
        not fault.startswith("relief-open:") for fault in frame.get("active_faults") or [])), None)
    first_hazard_s = incident["time_s"] if incident else None
    protective = next((action for action in actions if action["kind"] in
        ("operation.stop", "valve.close", "esd.trip", "access.restrict", "personnel.evacuate")
        and first_hazard_s is not None and action["issued_s"] >= first_hazard_s), None)
    response_delay_s = (max(0.0, protective["issued_s"] - first_hazard_s)
                        if protective and first_hazard_s is not None else None)
    failures = [action for action in actions if action["status"] == "failed"]
    premature = []
    for action in actions:
        if action["kind"] not in ("valve.open", "power.restore", "access.release"):
            continue
        preceding = next((frame for frame in reversed(frames)
                          if frame["time_s"] <= action["issued_s"]), None)
        if preceding and (preceding.get("total_leak_flow_g_s", 0) > .01 or
                          any(not fault.startswith("relief-open:")
                              for fault in preceding.get("active_faults") or [])):
            premature.append(action["id"])
    vent_events = [action["id"] for action in actions
                   if action["kind"] in ("vent.open", "purge.run")]
    possible_wrong_isolations = []
    secondary_hazards = []
    for action in actions:
        preceding = next((frame for frame in reversed(frames)
                          if frame["time_s"] <= action["issued_s"]), None)
        faults = (preceding or {}).get("active_faults") or []
        targets = [fault.split(":", 1)[1] for fault in faults if ":" in fault
                   and not fault.startswith("relief-open:")]
        if (action["kind"] == "valve.close" and action["target"].startswith("bank.") and
            targets and all(target.startswith("cascade.") for target in targets) and
            not any(action["target"].startswith("bank." + target.split(".")[1]) for target in targets)):
            possible_wrong_isolations.append(action["id"])
        if action["kind"] == "vent.open" and any(fault.startswith("external-fire:") for fault in faults):
            secondary_hazards.append({"action_id": action["id"],
                                      "reason": "화재 중 벤트 방출 위험 중첩"})
    peak_radius = max((_virtual_safety_metrics(frame)["effect_radius_m"] for frame in frames), default=0.0)
    response_penalty = (30 if first_hazard_s is not None and protective is None
                        else min(30, response_delay_s or 0))
    score = max(0, round(100 - response_penalty -
                       10 * len(failures) - 15 * len(premature) -
                       5 * len(possible_wrong_isolations) - 12 * len(secondary_hazards)))
    return {"first_hazard_s": first_hazard_s, "first_protective_action_s":
            protective["issued_s"] if protective else None,
            "response_delay_s": response_delay_s, "failed_action_ids": [a["id"] for a in failures],
            "premature_restore_ids": premature, "vent_release_action_ids": vent_events,
            "possible_wrong_isolation_ids": possible_wrong_isolations,
            "secondary_hazards": secondary_hazards,
            "peak_effect_sample_m": peak_radius, "training_score": score,
            "score_note": "가상 훈련 비교용 지표이며 실제 안전성·대응 적합성을 판정하지 않습니다."}


@app.post("/api/simulations/{job_id}/safety/compare")
def compare_virtual_safety_runs(job_id: str, request: VirtualTrainingCompareInput) -> dict[str, Any]:
    with _jobs_lock:
        jobs = [_jobs.get(job_id), _jobs.get(request.other_job_id)]
        if any(job is None for job in jobs):
            raise HTTPException(status_code=404, detail="Simulation not found")
        result = []
        for key, job in zip((job_id, request.other_job_id), jobs):
            frames = job["frames"]
            safety = _process_runtimes.get(key)
            fault_signature = _virtual_fault_signature(frames)
            result.append({"job_id": key, "duration_s": frames[-1]["time_s"] if frames else 0,
                           "fault_signature": fault_signature,
                           "peak_leak_flow_g_s": max((frame.get("total_leak_flow_g_s", 0) for frame in frames), default=0),
                           "released_mass_kg": frames[-1].get("released_mass_kg", 0) if frames else 0,
                           "peak_gas_volpct_h2": max((_virtual_safety_metrics(frame)["gas_max_volpct_h2"]
                                                     for frame in frames), default=0),
                           "esd_time_s": next((frame["time_s"] for frame in frames if frame.get("esd")), None),
                           "action_count": len(safety.safety.actions) if safety else 0,
                           "failed_actions": sum(action["status"] == "failed" for action in safety.safety.actions) if safety else 0,
                           "evaluation": _virtual_training_evaluation(job, safety.safety) if safety else None})
        return {"runs": result, "same_fault_signature": result[0]["fault_signature"] == result[1]["fault_signature"]}


def _virtual_fault_signature(frames: list[dict[str, Any]]) -> list[str]:
    """Compare physical fault inputs, not per-run generated release IDs."""
    return sorted(
        {fault for frame in frames for fault in frame.get("active_faults") or []
         if not fault.startswith(("relief-open:", "hydrogen-leak:"))} |
        {"release:" + str(release.get("component_id")) + ":" +
         f"{float(release.get('orifice_diameter_m') or 0):.6f}" for frame in frames
         for release in ((frame.get("hazop") or {}).get("releases") or [])
         if release.get("release_id") and not str(release["release_id"]).startswith(("vent-", "relief-"))})


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


def _invoke_saga_one_pass(prompt: str, provider: str,
                          on_token: Callable[[str], None] | None = None) -> dict[str, Any]:
    """Call SAGA's single-completion LLM route, never its RAG/review chat."""
    base = os.getenv("H2STATION_SAGA_URL", "http://127.0.0.1:8090").rstrip("/")
    endpoint = "/api/digital-twin/chat/direct/stream" if on_token else "/api/digital-twin/chat/direct"
    body = json.dumps({"message": prompt[:9900], "provider": provider, "max_tokens": 2200},
                      ensure_ascii=False).encode("utf-8")
    request = Request(base + endpoint, data=body, headers={"Content-Type": "application/json"})
    if on_token is None:
        with urlopen(request, timeout=35) as response:
            return json.load(response)
    final: dict[str, Any] | None = None
    event_name = ""
    data_lines: list[str] = []
    with urlopen(request, timeout=35) as response:
        for raw_line in response:
            line = raw_line.decode("utf-8").rstrip("\r\n")
            if line.startswith("event:"):
                event_name = line[6:].strip()
            elif line.startswith("data:"):
                data_lines.append(line[5:].strip())
            elif not line and data_lines:
                payload = json.loads("\n".join(data_lines))
                if event_name == "token":
                    on_token(str(payload.get("text") or ""))
                elif event_name == "answer":
                    final = payload
                elif event_name == "error":
                    raise URLError(str(payload.get("detail") or "SAGA 직답 스트림 오류"))
                event_name = ""
                data_lines.clear()
    if final is None:
        raise URLError("SAGA 직답 스트림에서 최종 답변을 받지 못했습니다.")
    return final


async def _invoke_saga_one_pass_selected(prompt: str, provider: str,
                                         stream_output: bool = False) -> dict[str, Any]:
    sink = _saga_token_sink.get() if stream_output else None
    return await asyncio.to_thread(_invoke_saga_one_pass, prompt, provider, sink)


def _invoke_isolated_twin_assistant(channel: Literal["main", "sensor"], payload: dict[str, Any],
                                    on_token: Callable[[str], None] | None = None) -> dict[str, Any]:
    """Call one isolated 8090 integration contract without SAGA chat/session state."""
    base = os.getenv("H2STATION_SAGA_URL", "http://127.0.0.1:8090").rstrip("/")
    endpoint = f"/api/integrations/digital-twin/{channel}"
    if on_token is not None:
        endpoint += "/stream"
    body = json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")
    request = Request(base + endpoint, data=body, headers={"Content-Type": "application/json"})
    if on_token is None:
        with urlopen(request, timeout=35) as response:
            return json.load(response)
    final: dict[str, Any] | None = None
    event_name = ""
    data_lines: list[str] = []
    with urlopen(request, timeout=35) as response:
        for raw_line in response:
            line = raw_line.decode("utf-8").rstrip("\r\n")
            if line.startswith("event:"):
                event_name = line[6:].strip()
            elif line.startswith("data:"):
                data_lines.append(line[5:].strip())
            elif not line and data_lines:
                event = json.loads("\n".join(data_lines))
                if event_name == "token":
                    on_token(str(event.get("text") or ""))
                elif event_name == "answer":
                    final = event
                elif event_name == "error":
                    raise URLError(str(event.get("detail") or f"{channel} 보조자 스트림 오류"))
                event_name = ""
                data_lines.clear()
    if final is None:
        raise URLError(f"{channel} 보조자 스트림에서 최종 답변을 받지 못했습니다.")
    return final


async def _invoke_main_assistant_selected(question: str, context: dict[str, Any],
                                           history: list[SagaChatTurn], provider: str,
                                           request_kind: str, stream_output: bool = False) -> dict[str, Any]:
    payload = {
        "question": question,
        "context": context,
        "history": [{"role": turn.role, "content": turn.content[:1200]} for turn in history[-8:]],
        "request_kind": request_kind,
        "provider": provider,
        "language": context.get("output_language", "ko"),
        "max_tokens": MAIN_ASSISTANT_MAX_TOKENS,
    }
    sink = _saga_token_sink.get() if stream_output else None
    return await asyncio.to_thread(_invoke_isolated_twin_assistant, "main", payload, sink)


async def _invoke_sensor_assistant_selected(sensor_id: str, question: str,
                                             context: dict[str, Any], provider: str,
                                             request_kind: str,
                                             stream_output: bool = False) -> dict[str, Any]:
    payload = {
        "sensor_id": sensor_id,
        "question": question,
        "context": context,
        "request_kind": request_kind,
        "provider": provider,
        "language": context.get("output_language", "ko"),
        "max_tokens": 2200,
    }
    sink = _saga_token_sink.get() if stream_output else None
    return await asyncio.to_thread(_invoke_isolated_twin_assistant, "sensor", payload, sink)


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
                answer = str(result.get("question_answer") or result.get("analysis_answer") or result.get("answer") or "")
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


def _align_direct_evaluation(
    result: dict[str, Any] | None, active_rules: list[dict[str, Any]],
    station_status: str,
) -> dict[str, Any] | None:
    """Keep SAGA's stateless threshold check from overriding mode-aware alarms.

    Zero flow is normal while a process is idle, and trapped pressure can be
    normal until a disconnect is requested. The simulator's rule engine knows
    those operating modes; SAGA's independent numeric check does not.
    """
    if result is None:
        return None
    triggered_tags = {str(rule.get("sensor_id")) for rule in active_rules
                      if rule.get("state") == "TRIGGER" and rule.get("sensor_id")}
    raw_hits = result.get("hits") if isinstance(result.get("hits"), list) else []
    hits = [hit for hit in raw_hits if isinstance(hit, dict)
            and str(hit.get("tag_id")) in triggered_tags]
    return {**result, "status": station_status, "hits": hits, "sop": {}}


def _direct_question_evidence(frame: dict[str, Any], catalog: dict[str, Any],
                              question: str, nodes: list[dict[str, Any]]) -> str:
    """Answer equipment/signal questions with the current numeric readings."""
    signals = (frame.get("hazop") or {}).get("signals") or {}
    if not signals:
        return ""
    node_ids = {str(node.get("node_id")) for node in nodes}
    normalized = re.sub(r"\s+", "", question)
    aliases = (("압축기", {"N03", "N04", "N05", "N06"}),
               ("프리쿨러", {"N12", "N16", "N19"}),
               ("트레일러", {"N01", "N02"}),
               ("차량1", {"N11", "N12", "N13", "N14"}),
               ("차량2", {"N15", "N16", "N17", "N18"}))
    for word, ids in aliases:
        if word in normalized:
            node_ids.update(ids)
    requested_tags = set(re.findall(r"(?:PT|TT|FT|GD|FD)-\d{4}", question.upper()))
    prefixes = {prefix for word, prefix in (("압력", "PT-"), ("온도", "TT-"),
                ("유량", "FT-"), ("가스", "GD-"), ("화염", "FD-")) if word in question}
    sensor_nodes = {str(sensor.get("sensor_id")): str(sensor.get("node_id"))
                    for sensor in catalog.get("sensors") or []}
    selected = [(tag, row) for tag, row in signals.items() if isinstance(row, dict)
                and (tag in requested_tags or sensor_nodes.get(tag) in node_ids
                     or not node_ids and not requested_tags and any(tag.startswith(prefix) for prefix in prefixes))]
    if not selected:
        return ""
    selected.sort(key=lambda item: (item[0][:2], item[0]))
    lines = ["**질문 관련 현재 신호**"]
    for tag, row in selected[:12]:
        value = row.get("value")
        rendered = f"{value:.3f}" if isinstance(value, (int, float)) else "값 없음"
        lines.append(f"- {tag}: {rendered} {row.get('unit') or ''} · 품질 {row.get('quality') or 'UNKNOWN'}")
    if len(selected) > 12:
        lines.append(f"- 관련 신호 {len(selected) - 12}개는 센서 화면에서 확인할 수 있습니다.")
    return "\n".join(lines)


def _direct_impact_summary(results: list[dict[str, Any]]) -> str:
    """Report only computed sample results, with their measured basis visible."""
    if not results:
        return ""
    node_names = {str(node.get("node_id")): str(node.get("설비_라인") or "")
                  for node in load_catalog()["nodes"]}
    lines = ["### 피해영향예측 · 현재 센서 기준"]
    for row in results[:3]:
        node = str(row.get("node_name") or node_names.get(str(row.get("node_id")))
                   or row.get("node_id") or "설비")
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
        plume = row.get("flammable_plume_streamline_distance_m")
        if isinstance(plume, (int, float)) and plume > 0:
            effect.append(f"4 vol% 비점화 플룸 중심선 거리 {plume:g} m")
        lines.append("  " + " · ".join(effect))
    validation_limit = next(
        (
            str(row["consequence_validation_claim_limit"])
            for row in results
            if row.get("consequence_validation_claim_limit")
        ),
        "표본점 결과는 현장 안전거리나 확정 대피반경이 아닙니다.",
    )
    lines.append(f"- 검증 범위: {validation_limit}")
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


def _direct_answer_conflicts_with_signals(
    answer: str, *, alert: bool = False, gas_observed: bool = False,
    physical_leak: bool = False, impact_calculated: bool = False,
) -> bool:
    """Reject a one-pass narrative that negates an already verified simulation fact.

    This is deliberately narrow: a hypothetical leak may be described as not
    real, but a measured gas signal or an active process release may not be
    denied. The deterministic answer remains available as a safe fallback.
    """
    compact = re.sub(r"[\s*`_·]", "", answer).lower()
    if alert and re.search(r"(?:현재|전체|공정|시스템)?(?:는|이)?(?:정상상태|정상운전|정상범위|이상없음|경보없음)", compact):
        if not re.search(r"(?:정상상태|정상운전|정상범위|이상없음|경보없음)(?:가|이)?(?:아니|아닙|아님|않)", compact):
            return True
    if gas_observed and (
        re.search(r"(?:수소|가스).{0,24}(?:감지|검출|관측).{0,18}(?:되지않|안되|없|미확인)", compact)
        or re.search(r"(?:수소|가스)농도(?:는|가)?0(?:\.0+)?(?:vol%|%)", compact)
    ):
        return True
    if physical_leak and re.search(
        r"(?:현재|실제|모의|공정)?(?:의)?(?:수소|가스)?누출(?:은|이|량은|량이)?"
        r"(?:없|미발생|발생하지않|확인되지않|관측되지않)", compact
    ):
        return True
    if impact_calculated and re.search(
        r"(?:피해영향|영향범위|사고영향).{0,18}"
        r"(?:계산되지않|미계산|결과(?:가|는|이)?없|평가되지않)", compact
    ):
        return True
    return False


def _impact_requested(question: str) -> bool:
    normalized = question.lower()
    return any(term in normalized for term in (
        "피해", "영향", "누출", "사고 범위", "위험 범위", "시나리오",
        "consequence", "impact", "leak", "release", "hazard distance",
        "risk distance", "scenario", "thermal radiation", "overpressure",
    ))


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
    if "압축기" in normalized:
        aliases.extend(["N03", "N04", "N05", "N06"])
    if "프리쿨러" in normalized or "냉각기" in normalized:
        aliases.extend(["N19", "N12", "N16"])
    if "트레일러" in normalized:
        aliases.extend(["N01", "N02"])
    if "차량1" in normalized or "1번차량" in normalized:
        aliases.extend(["N13", "N14"])
    if "차량2" in normalized or "2번차량" in normalized:
        aliases.extend(["N17", "N18"])
    if any(term in normalized for term in ("dispenser", "fuelinghose", "nozzle")):
        first = any(term in normalized for term in ("dispenser1", "dispenser#1", "vehicle1", "car1"))
        second = any(term in normalized for term in ("dispenser2", "dispenser#2", "vehicle2", "car2"))
        aliases.extend(["N13"] if first and not second else ["N17"] if second and not first else ["N13", "N17"])
    if any(term in normalized for term in ("storage", "bank", "cascade")):
        banks = {"high": "N09", "medium": "N08", "mid": "N08", "low": "N07"}
        requested = [node_id for word, node_id in banks.items() if word in normalized]
        aliases.extend(requested or ["N07", "N08", "N09"])
    if "compressor" in normalized:
        aliases.extend(["N03", "N04", "N05", "N06"])
    if "precool" in normalized or "chiller" in normalized:
        aliases.extend(["N19", "N12", "N16"])
    if "trailer" in normalized:
        aliases.extend(["N01", "N02"])
    if "vehicle1" in normalized or "car1" in normalized:
        aliases.extend(["N13", "N14"])
    if "vehicle2" in normalized or "car2" in normalized:
        aliases.extend(["N17", "N18"])
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
    english = request.question.lower()
    if "scenario" in english and any(word in english for word in
                                     ("create", "generate", "evaluate", "calculate", "compare", "propose")):
        return True
    if any(word in english for word in ("leak", "release")) and any(word in english for word in
            ("if", "hypothetical", "assume", "scenario")) and _impact_requested(english):
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
        "flammable_plume_streamline_distance_m은 비점화 수소 제트의 4 vol% 중심선 등농도 거리이며 구형 반경이나 확정 대피거리가 아닙니다. "
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
        runtime = _process_runtimes.get(job_id)
        if runtime is not None:
            # Streamed frames intentionally omit the rolling action history to
            # keep monitor traffic bounded.  Interactive LLM analyses need the
            # current feedback state, however, so attach it to this private
            # request snapshot without mutating the retained frame.
            frame["virtual_safety"] = {
                **(frame.get("virtual_safety") or {}),
                **runtime.safety.snapshot(),
            }
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
    show_impact_results = (emergency_context or request.scenario_mode
                           or (request.trigger == "manual" and _impact_requested(request.question)))
    if not request.direct and _scenario_requested(request):
        backend = await asyncio.to_thread(load_hyram_backend)
        return await _run_saga_scenario_analysis(frame, catalog, backend, request, active,
                                                 mentioned_ids, len(sensor_values))
    response_plans = response_selection(frame, catalog, request.question, request.trigger)
    virtual_safety = frame.get("virtual_safety") or {}
    recent_virtual_actions = (virtual_safety.get("actions") or [])[-5:]
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
        "flammable_contour_volume_fraction": (release.get("consequence") or {}).get("flammable_contour_volume_fraction"),
        "flammable_plume_streamline_distance_m": (release.get("consequence") or {}).get("flammable_plume_streamline_distance_m"),
        "modeled_consequence_mass_flow_kg_s": (release.get("consequence") or {}).get("modeled_consequence_mass_flow_kg_s"),
        "sampled_max_distance_m": (release.get("consequence") or {}).get("sampled_max_distance_m"),
        "sampled_next_distance_m": (release.get("consequence") or {}).get("sampled_next_distance_m"),
        "observation_point_count": (release.get("consequence") or {}).get("observation_point_count"),
        "effect_range_status": (release.get("consequence") or {}).get("effect_range_status"),
        "consequence_validation_scope": (release.get("consequence") or {}).get("consequence_validation_scope"),
        "geometry_display_mapping_verified": (release.get("consequence") or {}).get("geometry_display_mapping_verified"),
        "source_depletion_external_holdout_supported": (release.get("consequence") or {}).get("source_depletion_external_holdout_supported"),
        "full_station_vehicle_validation_supported": (release.get("consequence") or {}).get("full_station_vehicle_validation_supported"),
        "site_specific_safety_distance_supported": (release.get("consequence") or {}).get("site_specific_safety_distance_supported"),
        "consequence_validation_artifacts": (release.get("consequence") or {}).get("consequence_validation_artifacts"),
        "consequence_validation_claim_limit": (release.get("consequence") or {}).get("consequence_validation_claim_limit"),
        "range_interpretation": ("표본 관측점에서 5 kW/m² 및 5 kPa 기준 미달; 영향 반경 미확정"
            if (release.get("consequence") or {}).get("effect_range_status") == "BELOW_THRESHOLDS_AT_SAMPLES"
            else "관측점의 임계값 초과 거리만 확인; 현장 안전반경 아님")}
        for release in releases[:5] if isinstance(release, dict)]
    assessed_releases = {row.get("release_id") for row in sensor_impacts if row.get("calculation_status") == "calculated"}
    impact_results = [row for row in sensor_impacts + [row for row in legacy_impacts
        if row.get("release_id") not in assessed_releases]
        if row.get("calculation_status") == "calculated"]
    evidence_manifest = build_evidence_manifest(
        frame, sensor_values, impact_results, show_impact_results,
        active_conditions=matched_rules + reference_rules,
        question=request.question,
    )
    if request.direct:
        # Keep the live monitor on the dedicated low-latency API even for
        # alarms. Consequences are calculated first from this same snapshot;
        # an unavailable SAGA process falls back to local deterministic data,
        # never to the slower generative chat endpoint.
        direct_result = await asyncio.to_thread(
            _invoke_saga_hazop_direct, frame, catalog, str(job_id), request.question, impact_results
        )
        direct_result = _align_direct_evaluation(direct_result, active, alert_status)
        direct_sop = (direct_result or {}).get("sop") if isinstance((direct_result or {}).get("sop"), dict) else {}
        direct_hits = (direct_result or {}).get("hits") if isinstance((direct_result or {}).get("hits"), list) else []
        actual_alert = emergency_context
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
        answer, direct_claim_guard = guard_llm_claims(answer, evidence_manifest)
        llm_model = "SAGA 직답 · 센서 기반 계산"
        llm_error = None
        llm_claim_guard = direct_claim_guard
        if request.one_pass:
            focused_tags = {rule.get("sensor_id") for rule in matched_rules + reference_rules}
            focused_tags.update(re.findall(r"(?:PT|TT|FT|GD|FD)-\d{4}", request.question.upper()))
            selected_values = {tag: value for tag, value in sensor_values.items() if tag in focused_tags}
            if not selected_values:
                selected_values = dict(list(sensor_values.items())[:36])
            prompt_data = {
                "output_language": request.language,
                "impact_calculation_attempted": show_impact_results,
                "impact_results": impact_results[:3],
                "evidence_basis": prompt_decision_evidence(evidence_manifest),
                "recent_dialogue": [{"role": turn.role, "content": turn.content[:400]}
                                    for turn in request.history[-4:]],
                "simulation_time_s": frame.get("time_s"),
                "station_status": alert_status,
                "findings": analysis.get("findings") or [],
                "active_faults": frame.get("active_faults") or [],
                "relief_valves_open": frame.get("relief_valves_open") or [],
                "current_signals": selected_values,
                "active_conditions": matched_rules,
                "related_conditions": reference_rules[:8],
                "direct_evaluation": {"status": (direct_result or {}).get("status"),
                                      "hits": direct_hits[:8]},
                "consolidated_response_guidance": _prompt_response_guidance_summary(
                    structured_guidance(response_plans, actual_alert=actual_alert)
                ),
            }
            try:
                reply = await _invoke_main_assistant_selected(
                    request.question, prompt_data, request.history, request.provider,
                    "user_query" if request.trigger == "manual" else "automatic_analysis",
                    stream_output=True,
                )
                llm_answer = _safe_saga_text(str(reply.get("answer") or ""))
                llm_answer, llm_claim_guard = guard_llm_claims(
                    llm_answer, evidence_manifest
                )
                gas_observed = any(
                    tag.startswith("GD-") and value.get("quality") == "GOOD"
                    and isinstance(value.get("value"), (int, float)) and value["value"] > 0
                    for tag, value in sensor_values.items()
                )
                if llm_answer and _direct_answer_conflicts_with_signals(
                    llm_answer, alert=actual_alert, gas_observed=gas_observed,
                    physical_leak=any(float(release.get("mass_flow_g_s") or 0) > .001
                                      and not str(release.get("release_id") or "").startswith("relief-")
                                      for release in releases if isinstance(release, dict)),
                    impact_calculated=bool(impact_results),
                ):
                    llm_model = "SAGA 직답 · 센서값 검증"
                elif llm_answer:
                    answer = llm_answer
                    llm_model = str(reply.get("model") or "SAGA 단일 답변")
                else:
                    llm_error = "직답 LLM이 빈 응답을 반환했습니다."
            except (URLError, HTTPError, TimeoutError, OSError, ValueError) as exc:
                llm_error = ("SAGA 직답 LLM에 연결하지 못했습니다. SAGA 서버의 직답 API와 선택한 제공자 설정을 "
                             f"확인하세요. ({exc})")
            if llm_error:
                answer = f"**{llm_error}**\n\n" + answer
        evidence = _direct_question_evidence(frame, catalog, request.question, mentioned_nodes)
        if evidence and request.language == "ko":
            answer = answer + "\n\n" + evidence if request.one_pass else evidence + "\n\n" + answer
        question_answer = answer
        if actual_alert and alert_status == "NORMAL":
            alert_status = "WARNING"
        impact_text = _direct_impact_summary(impact_results) if show_impact_results else ""
        if impact_text and request.language == "ko":
            answer += "\n\n" + impact_text
        elif show_impact_results and request.language == "ko":
            answer += "\n\n현재 센서 기준 정량 피해영향 결과는 확보되지 않았습니다."
        if recent_virtual_actions and request.language == "ko":
            last = recent_virtual_actions[-1]
            if float(frame.get("time_s") or 0) - float(last.get("issued_s") or 0) <= 15:
                label = {"confirmed": "완료", "failed": "실패", "commanded": "동작 확인 대기"}.get(
                    last.get("status"), "피드백 확인 중")
                answer += (f"\n\n**최근 가상 안전조치:** {last.get('kind')} / {last.get('target')} · {label}. "
                           "밸브 피드백과 유량 변화는 안전 대응 리모콘의 사건 기록에서 확인하세요.")
        analysis_answer = question_answer if request.language == "en" else answer
        wants_procedures = (request.trigger != "manual" or not request.one_pass or
                            any(term in request.question for term in
                                ("조치", "대응", "대피", "격리", "차단", "복구", "재가동", "안전관리", "절차")))
        guidance = render_guidance(response_plans, actual_alert=actual_alert) if wants_procedures else ""
        if guidance and request.language == "ko":
            answer += "\n\n---\n\n" + guidance
        return {
            "time_s": frame.get("time_s"), "trigger": request.trigger,
            "scenario_mode": bool(request.scenario_mode),
            "answer": answer, "analysis_answer": analysis_answer,
            "question_answer": question_answer,
            "response_guidance": (structured_guidance(response_plans, actual_alert=actual_alert)
                                  if wants_procedures else None),
            "model": llm_model,
            "llm_error": llm_error,
            "active_rule_ids": sorted(ids), "sensor_count": len(sensor_values),
            "risk_assessment": {"status": alert_status, "score": analysis.get("score"),
                                "findings": analysis.get("findings") or [],
                                "calculated_impact_count": len(impact_results)},
            "show_impact_results": show_impact_results,
            "impact_results": impact_results,
            "evidence_manifest": evidence_manifest,
            "llm_claim_guard": llm_claim_guard,
            "hazop_direct": direct_result,
            "hazop_sop": direct_sop,
            "hazop_hit_count": len(direct_hits),
        }
    # The full live frame can contain many unrelated GOOD channels.  Preserve
    # the question/alarm/detector channels first, then add a deterministic
    # bounded sample.  The full signal set remains in the frame and API
    # response; this only protects provider prompt budget.
    prompt_sensor_tags = set(reference_tags)
    prompt_sensor_tags.update(
        str(rule.get("sensor_id"))
        for rule in matched_rules + reference_rules
        if rule.get("sensor_id")
    )
    prompt_sensor_tags.update(
        tag for tag in sensor_values if tag.startswith(("GD-", "FD-"))
    )
    prompt_sensor_values: dict[str, Any] = {}
    for tag in list(sorted(prompt_sensor_tags)) + sorted(sensor_values):
        if tag in sensor_values:
            prompt_sensor_values[tag] = sensor_values[tag]
        if len(prompt_sensor_values) >= 48:
            break
    context = {
        # Keep the compact, safety-critical facts at the front of the bounded
        # prompt.  The serialized context is deliberately capped below, so
        # bulky evidence/telemetry must not crowd out the registered HAZOP
        # rules that explain the current alarm.
        "impact_results":impact_results,
        "evidence_basis": prompt_decision_evidence(evidence_manifest),
        "hazop_reference_rules":reference_rules,
        "hazop_active":active, "hazop_rules":matched_rules,
        "consolidated_response_guidance": _prompt_response_guidance_summary(
            structured_guidance(response_plans, actual_alert=emergency_context)
        ),
        "impact_calculation_attempted":show_impact_results,
        "station":"H70 reference simulation", "time_s":frame.get("time_s"),
        "fire_detection": analysis.get("fire_detection"),
        "flame_detector_signals": frame.get("flame_detectors") or {},
        "active_faults":frame.get("active_faults"),
        "analysis":analysis,
        "virtual_safety_actions": [{key: row.get(key) for key in
            ("kind", "target", "issued_s", "completed_s", "status", "baseline_metrics", "after_metrics")}
            for row in recent_virtual_actions],
        "virtual_safety_state": {key: virtual_safety.get(key) for key in
            ("ventilation", "cooling", "personnel", "evacuated", "access_restricted",
             "power_isolated", "recovery_approved")},
        "relief_valves_open":frame.get("relief_valves_open") or [],
        "relief_valve_settings":{key: value for key, value in
            (((frame.get("process_operations") or {}).get("settings") or {}).get("relief_valves") or {}).items()
            if key in (frame.get("relief_valves_open") or [])},
        "reference_sensor_values":{tag: value for tag, value in sensor_values.items() if tag in reference_tags},
        "sensor_values":prompt_sensor_values,
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
        "evidence_basis를 응답의 근거 목록으로 사용하고 evidence_digest를 임의로 바꾸지 마세요. "
        "public_operating_envelope_screen이 있으면 현재 모의 노즐 유량을 공개 고유량 실험의 집계 평균·최대값과 비교한 보조 screen으로만 설명하세요. "
        "이 screen을 모델 검증 통과, 실제 충전소 성능, 프로토콜 적합성 또는 안전 인증으로 표현하지 마세요. raw_rows_public=false이면 공개 원시 시계열이 없다는 한계를 함께 밝히세요. "
        "runtime_calibration.status=active이면 비식별 실측 저장 뱅크 경계 보정이 이번 실행에 적용된 것이며, 재충전 여유폭 해석에만 사용하세요. "
        "status가 reference_defaults이면 기준 모델이고, requested_unavailable이면 보정을 적용하지 못한 기준 모델입니다. 어느 상태도 차량·디스펜서·전체 충전루프 검증을 뜻하지 않습니다. "
        "public accident action category counts는 대응계획의 근거 범위만 나타내며, 조치의 효과나 사고확률을 의미하지 않습니다. "
        "confidential_local_accident_response_coverage는 비식별 실제 사고 메타데이터와 5단계 대응계획의 구조적 연결성만 뜻하며, 사고 원문·현장 효과·확률·물리 검증으로 해석하지 마세요. "
        "impact_results의 계산 성공 항목만 수치 결과로 설명하세요. "
        "각 impact_results의 consequence_validation_scope가 COMPONENT_SCREENING_BOUNDED이면, "
        "외부 비밀폐 자유제트의 구성요소 수준 표본 표시 근거와 실제 설비·감압·배치·충전소-차량 전체 루프·현장 안전거리 검증의 부재를 구분하세요. "
        "consequence_validation_claim_limit을 무시하거나 이를 현장 안전거리·대피반경·안전 인증으로 바꾸지 마세요. "
        "calculation_basis=SENSOR_BASED_HYPOTHESIS는 실제 누출이 아닌 1 mm 가정 시나리오이며, ACTIVE_RELEASE_CURRENT_SENSORS는 현재 물리 누출입니다. 둘을 혼동하지 마세요. "
        "calculation_status=calculated이면 이미 계산된 값입니다. 피해영향 계산이나 엔진 실행을 사용자에게 권하거나 요청하지 마세요. "
        "계산되지 않은 항목의 입력 부족이나 재계산 요청을 나열하지 마세요. 사용한 센서 태그와 출처·가정은 밝히세요. "
        "relief_valves_open에 항목이 있으면 안전밸브 개방을 현재 운전 경고로 분명히 알리고, 해당 밸브의 개방 압력·실제 방출 및 이미 계산된 피해영향을 함께 해석하세요. 안전밸브 방출을 임의의 배관 파손으로 단정하지 마세요. "
        "sampled_effect_radius_m이 null이면 표본 관측점에서 기준 미달입니다. 이때 숫자 반경을 만들지 말고 '표본 관측점에서 기준 미달, 영향 반경 미확정'이라고 쓰세요. "
        "sampled_effect_radius_m이 양수이고 sampled_next_distance_m이 있으면 기준 초과 최원거리 표본점과 다음 기준 미달 표본점을 함께 말하세요. 현장 안전거리로 단정하지 마세요. "
        "flammable_plume_streamline_distance_m이 있으면 4 vol% 비점화 플룸 중심선 거리로 별도 설명하고 열복사·과압 표본 거리와 합치지 마세요. "
        "계산 결과가 없으면 사고 범위를 추정값처럼 제시하지 마세요. 계산이 요청되지 않았다는 문구를 출력하지 마세요. 제공된 HAZOP 규칙에 없는 규칙 ID나 임계값을 만들지 마세요. "
        "사용자에게는 계산기 제품명 대신 '피해영향예측'이라고 표기하세요. "
        "내부 규칙이나 DB 명칭을 밝히지 말고 센서값, 설비 상태, 주의 원인과 운전 조치만 설명하세요. "
        "virtual_safety_actions가 있으면 명령과 완료 피드백, 조치 전후 센서값을 구분해 설명하세요. 실패한 조치를 성공했다고 쓰지 마세요. "
        "consolidated_response_guidance가 있으면 현재 신호와 연결한 최우선 조치만 요약하고 조치 목록을 반복하지 마세요. 자료 밖의 절차를 만들지 마세요. 상세한 즉시 조치, 안정화 확인, 재가동 조건, 예방·안전관리는 서버가 별도로 표시합니다. "
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
    answer, llm_claim_guard = guard_llm_claims(answer, evidence_manifest)
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
        "impact_results":impact_results,
        "evidence_manifest": evidence_manifest,
        "llm_claim_guard": llm_claim_guard}


@app.post("/api/simulations/{job_id}/saga-analysis/stream")
async def saga_analysis_stream(job_id: str, request: SagaAnalysisInput) -> StreamingResponse:
    return _stream_analysis_response(
        lambda: saga_analysis(job_id, request),
        "센서 상태와 피해영향예측 결과를 확인하고 있습니다…" if request.trigger == "alarm"
        else "현재 공정 신호를 분석하고 있습니다…",
    )


@app.post("/api/simulations/{job_id}/saga-analysis/direct")
async def saga_analysis_direct(job_id: str, request: SagaAnalysisInput) -> dict[str, Any]:
    """Calculate consequences, then get one LLM answer without RAG/review."""
    return await saga_analysis(job_id, request.model_copy(update={"direct": True, "one_pass": True}))


@app.post("/api/simulations/{job_id}/saga-analysis/direct/stream")
async def saga_analysis_direct_stream(job_id: str, request: SagaAnalysisInput) -> StreamingResponse:
    return _stream_analysis_response(
        lambda: saga_analysis_direct(job_id, request),
        "현재 센서와 피해영향예측 결과를 확인하고 있습니다…",
    )


@app.post("/api/simulations/{job_id}/assistants/main")
async def main_monitor_assistant(job_id: str, request: MainAssistantInput) -> dict[str, Any]:
    """Main-screen assistant boundary with no sensor-workbench or RAG modes."""
    internal = SagaAnalysisInput(
        provider=request.provider, question=request.question, trigger=request.trigger,
        scenario_mode=request.scenario_mode, direct=True, one_pass=True, history=request.history,
        language=request.language,
    )
    return await saga_analysis(job_id, internal)


@app.post("/api/simulations/{job_id}/assistants/main/stream")
async def main_monitor_assistant_stream(job_id: str,
                                        request: MainAssistantInput) -> StreamingResponse:
    return _stream_analysis_response(
        lambda: main_monitor_assistant(job_id, request),
        "현재 센서와 피해영향예측 결과를 확인하고 있습니다…",
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
        runtime = _process_runtimes.get(job_id)
        if selected is latest and runtime is not None:
            # Do not attach current action feedback to an historical sensor
            # frame: that would falsely make a later command look complete at
            # the selected earlier simulation time.
            frame["virtual_safety"] = {
                **(frame.get("virtual_safety") or {}),
                **runtime.safety.snapshot(),
            }
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
                      "executable_actions": suggested_actions(classify_rule(rule), sensor["node_id"]),
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
               "virtual_safety": frame.get("virtual_safety") or {},
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


def _sensor_response_guidance(
    frame: dict[str, Any],
    catalog: dict[str, Any],
    question: str,
    active_rules: list[dict[str, Any]],
    related_rules: list[dict[str, Any]],
    applicable_plan_ids: dict[str, None],
    known_plans: dict[str, dict[str, Any]],
) -> tuple[str, dict[str, Any] | None]:
    """Return trusted response steps that a generated answer cannot omit.

    The LLM explains the current evidence. Emergency and prevention steps come
    from the versioned response catalogue so provider/model changes cannot
    silently remove operator guidance from the selected-sensor view.
    """
    relevant_rules = active_rules + related_rules
    actual_alert = bool(relevant_rules)
    if actual_alert:
        selected = response_selection(frame, catalog, question, "alarm", limit=None)
        rule_ids = {str(rule.get("rule_id")) for rule in relevant_rules}
        plan_ids = set(applicable_plan_ids)
        focused = [item for item in selected
                   if str(item["plan"].get("rule_id")) in rule_ids
                   or (not item["plan"].get("rule_id") and item["plan"].get("id") in plan_ids)]
        if not focused:
            evidence = [str(rule.get("scenario") or rule.get("rule_id") or "관련 경보")
                        for rule in relevant_rules[:4]]
            focused = [{"plan": known_plans[plan_id], "evidence": evidence, "score": 0}
                       for plan_id in applicable_plan_ids if plan_id in known_plans][:4]

        def unique(items: list[Any], limit: int | None = None) -> list[Any]:
            result, seen = [], set()
            for item in items:
                key = re.sub(r"\s+", " ", str(item)).strip()
                if not key or key in seen:
                    continue
                seen.add(key)
                result.append(item)
                if limit is not None and len(result) >= limit:
                    break
            return result

        # Several thresholds from one detector are evidence for one developing
        # event, not separate incidents. Group by response family before making
        # the operator checklist.
        grouped: dict[str, dict[str, Any]] = {}
        for item in focused:
            plan_id = str(item["plan"]["id"])
            base = known_plans.get(plan_id, item["plan"])
            group = grouped.setdefault(plan_id, {"id": plan_id, "title": base["title"],
                                                  "plan": base, "evidence": [], "rules": []})
            group["evidence"].extend(item.get("evidence") or [])
            if item["plan"].get("rule_id"):
                group["rules"].append(item["plan"].get("title"))
        groups = list(grouped.values())[:4]
        for group in groups:
            group["evidence"] = unique(group["evidence"], 4)
            group["rules"] = unique(group["rules"], 3)

        rules_by_plan: dict[str, list[dict[str, Any]]] = {}
        for rule in relevant_rules:
            rules_by_plan.setdefault(str(rule.get("response_plan_id")), []).append(rule)
        executable: list[dict[str, str]] = []
        for group in groups:
            linked = rules_by_plan.get(group["id"]) or relevant_rules[:1]
            for rule in linked:
                executable.extend(suggested_actions(group["id"], rule.get("node_id")))
        unique_actions, action_keys = [], set()
        for action in executable:
            key = (action["kind"], action["target"])
            if key not in action_keys:
                action_keys.add(key)
                unique_actions.append(action)

        plans_for_groups = [group["plan"] for group in groups]
        recognition = unique([step for plan in plans_for_groups for step in plan["recognition"]], 5)
        immediate = unique([action["label"] for action in unique_actions]
                           + [step for plan in plans_for_groups for step in plan["immediate"]], 9)
        stabilize = unique([step for plan in plans_for_groups for step in plan["stabilize"]], 7)
        restart = unique([step for plan in plans_for_groups for step in plan["restart"]], 6)
        prevention = unique([step for plan in plans_for_groups for step in plan["prevention"]], 9)
        playbooks = load_playbooks()
        if len(playbooks.get("common_response") or []) >= 4:
            immediate = unique(immediate + [playbooks["common_response"][3]], 10)

        def numbered(steps: list[str]) -> str:
            return "\n".join(f"{index}. {step}" for index, step in enumerate(steps, 1))

        scenario_lines = []
        for index, group in enumerate(groups, 1):
            evidence = "; ".join(group["evidence"]) or "현재 선택 센서와 관련 구역 신호"
            scenario_lines.append(f"{index}. **{group['title']}**\n   - 판단 근거: {evidence}")
        alert_count = len(relevant_rules)
        family_count = len(groups)
        sections = [
            "### 종합 안전판단",
            (f"> **판단** 서로 연동된 경보 조건 {alert_count}건을 별도 사고로 나열하지 않고, "
             f"공통 원인과 사고 전개가 같은 **{family_count}개 대응 시나리오**로 통합했습니다. "
             "아래 순서대로 실행하고, 각 단계의 완료 조건을 확인한 뒤 다음 단계로 이동하세요."),
            "#### 발생 가능한 시나리오\n" + "\n".join(scenario_lines),
            "### 즉시 실행할 단계별 대응",
            "**1단계 · 상황 확인**\n" + numbered(recognition),
            "**2단계 · 공정 정지·격리 및 인원 보호**\n" + numbered(immediate),
            "**3단계 · 안정화 확인**\n" + numbered(stabilize),
            "**4단계 · 복구·재가동 전 확인**\n" + numbered(restart),
            "### 단계별 예방·안전관리",
        ]
        prevention_groups = {"설비 건전성 관리": [], "검지·차단 보호계통 관리": [],
                             "절차·교육·기록 관리": []}
        for step in prevention:
            if any(term in step for term in ("검지", "경보", "차단", "인터록", "환기", "ESD")):
                key = "검지·차단 보호계통 관리"
            elif any(term in step for term in ("훈련", "대피", "연락", "도면", "절차", "기록")):
                key = "절차·교육·기록 관리"
            else:
                key = "설비 건전성 관리"
            prevention_groups[key].append(step)
        stage_number = 1
        for title, steps in prevention_groups.items():
            if steps:
                sections.append(f"**{stage_number}단계 · {title}**\n" + numbered(steps))
                stage_number += 1

        source_ids = unique([source_id for plan in plans_for_groups
                             for source_id in plan.get("sources", [])])
        sources = [playbooks["sources"][source_id] for source_id in source_ids
                   if source_id in playbooks["sources"]]
        if sources:
            sections.append("**근거 자료**\n" + ", ".join(
                f"[{source['title']}]({source['url']})" for source in sources))
        consolidated = {
            "actual_alert": True,
            "mode": "consolidated",
            "intro": "연동 경보를 공통 원인별로 묶은 단일 운전자 행동계획입니다.",
            "common_steps": [],
            "scenarios": [{"id": group["id"], "title": group["title"],
                           "evidence": group["evidence"], "combined_conditions": group["rules"]}
                          for group in groups],
            "plans": [{"id": "consolidated_response", "title": "종합 대응계획",
                       "evidence": unique([entry for group in groups for entry in group["evidence"]], 8),
                       "recognition": recognition, "immediate": immediate,
                       "stabilize": stabilize, "restart": restart,
                       "prevention": prevention, "executable_actions": unique_actions,
                       "sources": sources}],
        }
        return "\n\n".join(sections), consolidated

    # Healthy sensors deliberately show routine prevention only. Emergency,
    # stabilization and restart instructions belong to warning/alarm states.
    playbooks = load_playbooks()
    source_index = playbooks["sources"]
    parts = ["### 예방·안전관리",
             "현재 선택 센서는 정상 범위입니다. 아래 항목을 평상시 점검과 사고 예방에 활용하세요."]
    structured_plans = []
    for plan_id in list(applicable_plan_ids)[:4]:
        plan = known_plans.get(plan_id)
        if not plan:
            continue
        prevention = list(dict.fromkeys(str(step) for step in plan.get("prevention", []) if step))
        if not prevention:
            continue
        sources = [source_index[key] for key in plan.get("sources", []) if key in source_index]
        section = [f"#### {plan['title']}", "\n".join(f"- {step}" for step in prevention)]
        if sources:
            section.append("근거 자료: " + ", ".join(
                f"[{source['title']}]({source['url']})" for source in sources))
        parts.append("\n\n".join(section))
        structured_plans.append({"id": plan["id"], "title": plan["title"],
                                 "prevention": prevention, "sources": sources})
    if not structured_plans:
        return "", None
    return "\n\n".join(parts), {"actual_alert": False, "common_steps": [],
                                   "plans": structured_plans}


def _prompt_response_guidance_summary(guidance: dict[str, Any] | None) -> dict[str, Any] | None:
    """Bound staged guidance before placing it in a sensor LLM prompt.

    The complete five-stage response plan is returned to the UI and appended
    after the answer.  Passing that entire plan to the model duplicates text
    and can crowd current gas/release evidence out of the provider context.
    This summary preserves the public scenario title, evidence, and first
    practical response steps while deliberately retaining the full plan
    outside the generative prompt. Internal plan IDs and selection modes are
    excluded because they are implementation details, not operator evidence.
    """
    if not isinstance(guidance, dict):
        return None
    actual_alert = guidance.get("actual_alert") is True
    plans: list[dict[str, Any]] = []
    for raw in guidance.get("plans") or []:
        if not isinstance(raw, dict):
            continue
        plan = {"title": raw.get("title")} if raw.get("title") is not None else {}
        evidence = raw.get("evidence") or []
        if evidence:
            plan["evidence"] = [str(item) for item in evidence[:2]]
        if actual_alert:
            plan["immediate"] = [str(item) for item in (raw.get("immediate") or [])[:2]]
            plan["stabilize"] = [str(item) for item in (raw.get("stabilize") or [])[:1]]
        else:
            plan["prevention"] = [str(item) for item in (raw.get("prevention") or [])[:2]]
        plans.append(plan)
        if len(plans) >= 3:
            break
    return {
        "actual_alert": actual_alert,
        "plan_count": len(guidance.get("plans") or []),
        "plans": plans,
        "full_plan_delivered_separately": True,
    }


@app.post("/api/simulations/{job_id}/sensors/{sensor_id}/analyze")
async def analyze_simulation_sensor(job_id: str, sensor_id: str,
                                    request: SensorAnalysisInput) -> dict[str, Any]:
    payload, frame, catalog = _sensor_analysis_context(job_id, sensor_id, request.time_s)
    active_rules = [rule for rule in payload["rules"] if rule["active"]]
    related_rules = payload["related_active_rules"]
    alert = payload["sensor_status"] == "ALERT"
    impact_results: list[dict[str, Any]] = []
    current_triggers = [rule for rule in active_rules + related_rules if rule.get("state") == "TRIGGER"]
    if current_triggers or _impact_requested(request.question):
        backend = await asyncio.to_thread(load_hyram_backend)
        assessed = await asyncio.to_thread(assess_sensor_cases, frame, catalog, backend,
                                           [payload["sensor"]["node_id"]])
        impact_results = [item for item in assessed if item.get("calculation_status") == "calculated"][:2]
    evidence_manifest = build_evidence_manifest(
        frame, payload["related_signals"], impact_results,
        bool(current_triggers or _impact_requested(request.question)),
        active_conditions=active_rules + related_rules,
        selected_sensor=sensor_id,
        question=request.question,
    )
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
    response_markdown, response_guidance = _sensor_response_guidance(
        frame, catalog, request.question, active_rules, related_rules,
        applicable_plan_ids, known_plans,
    )
    if request.direct:
        # Scope the direct evaluation to the selected equipment. The detailed
        # rules and staged plans are already returned by the sensor detail API.
        focused_frame = {**frame, "hazop": {**(frame.get("hazop") or {}),
                         "signals": payload["related_signals"]}}
        direct_result = await asyncio.to_thread(
            _invoke_saga_hazop_direct, focused_frame, catalog, str(job_id),
            request.question or f"{sensor_id} 현재 상태", impact_results,
        )
        direct_result = _align_direct_evaluation(
            direct_result, active_rules + related_rules,
            "WARNING" if current_triggers else "NORMAL",
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
            if any(term in request.question for term in ("왜", "원인", "위험", "상세")):
                causes = list(dict.fromkeys(str(rule.get("cause")) for rule in current_rules if rule.get("cause")))
                if causes:
                    lines.append("**가능한 원인:** " + "; ".join(causes[:3]))
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
        direct_answer, direct_claim_guard = guard_llm_claims(direct_answer, evidence_manifest)
        if current_rules and re.search(r"(?:정상\s*운전|정상\s*범위|이상\s*없|경보\s*없)", direct_answer):
            direct_answer = ""
        if direct_answer and (current_rules or payload["sensor_status"] == "NORMAL"):
            lines.append(direct_answer)
        impact_text = _direct_impact_summary(impact_results)
        if impact_text:
            lines.append(impact_text)
        recent_actions = (payload.get("virtual_safety") or {}).get("actions") or []
        if recent_actions:
            action = recent_actions[-1]
            if float(payload["time_s"] or 0) - float(action.get("issued_s") or 0) <= 15:
                lines.append("**최근 가상 조치** " + str(action.get("kind")) + " / " +
                             str(action.get("target")) + " · " + str(action.get("status")))
        answer = "\n\n".join(lines)
        llm_model = "SAGA 직답 · 센서 기반 계산"
        llm_error = None
        llm_claim_guard = direct_claim_guard
        if request.one_pass:
            prompt_data = {
                "output_language": request.language,
                "time_s": payload["time_s"], "selected_sensor": sensor_id,
                "selected_signal": signal, "sensor_status": payload["sensor_status"],
                "equipment": label, "related_signals": payload["related_signals"],
                "impact_results": impact_results,
                "evidence_basis": prompt_decision_evidence(evidence_manifest),
                "current_conditions": current_rules,
                "retained_conditions": [rule for rule in active_rules + related_rules
                                         if rule.get("state") != "TRIGGER"][:4],
                "gas_detection": gas,
                "current_release": release,
                "consolidated_response_guidance": _prompt_response_guidance_summary(response_guidance),
            }
            try:
                reply = await _invoke_sensor_assistant_selected(
                    sensor_id, request.question, prompt_data, request.provider,
                    "user_query" if request.question.strip() else "automatic_analysis",
                    stream_output=True,
                )
                llm_answer = _safe_saga_text(str(reply.get("answer") or ""))
                llm_answer, llm_claim_guard = guard_llm_claims(llm_answer, evidence_manifest)
                if llm_answer and _direct_answer_conflicts_with_signals(
                    llm_answer, alert=bool(current_rules),
                    gas_observed=bool(gas.get("hydrogen_observed")),
                    physical_leak=release.get("physical_leak_g_s", 0) > .001,
                    impact_calculated=bool(impact_results),
                ):
                    llm_model = "SAGA 직답 · 센서값 검증"
                elif llm_answer:
                    verified = [lines[1]]
                    if gas.get("hydrogen_observed"):
                        verified.append(f"수소 농도 {gas['value_volpct_h2']:.3f} vol% 관측")
                    if release.get("physical_leak_g_s", 0) > 0.001:
                        verified.append(f"모의 공정 누출 {release['physical_leak_g_s']:.3f} g/s")
                    if impact_text:
                        verified.append(impact_text)
                    answer = (llm_answer if request.language == "en" else
                              llm_answer + "\n\n**현재 확인값**\n" + "\n".join(
                                  f"- {item}" if not item.startswith("###") else item for item in verified))
                    llm_model = str(reply.get("model") or "SAGA 단일 답변")
                else:
                    llm_error = "직답 LLM이 빈 응답을 반환했습니다."
            except (URLError, HTTPError, TimeoutError, OSError, ValueError) as exc:
                llm_error = ("SAGA 직답 LLM에 연결하지 못했습니다. SAGA 서버의 직답 API와 선택한 제공자 설정을 "
                             f"확인하세요. ({exc})")
            if llm_error:
                answer = f"**{llm_error}**\n\n" + answer
        if response_markdown and request.language == "ko":
            answer = answer.rstrip() + "\n\n---\n\n" + response_markdown
        return {"sensor_id": sensor_id, "time_s": payload["time_s"],
                "answer": answer, "model": llm_model, "llm_error": llm_error,
                "impact_results": impact_results,
                "evidence_manifest": evidence_manifest,
                "active_rule_count": len(active_rules), "related_active_count": len(related_rules),
                "sensor_status": payload["sensor_status"], "hazop_direct": direct_result,
                "response_guidance": response_guidance,
                "llm_claim_guard": llm_claim_guard}
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
    context = {
        # Put live sensor/release evidence before prompt-only plan or
        # provenance summaries.  The complete staged plan is attached to the
        # API response after the model explains this snapshot.
        "time_s": payload["time_s"], "sensor": {
            "tag": sensor_id, "type": payload["sensor"].get("종류"),
            "location": payload["sensor"].get("설치_측정위치"), "node": payload["node"].get("설비_라인"),
            "current": payload["signal"], "mapping": payload["mapping"]},
        "sensor_status": payload["sensor_status"],
        "detection_summary": {"observed_hydrogen_readings": observed_gas,
                              "current_gas_alerts": current_gas_alerts,
                              "retained_gas_alarm_tags": retained_gas_alerts},
        "selected_gas_signal_evidence": payload["gas_signal_evidence"],
        "simulated_release_evidence": payload["simulated_release_evidence"],
        "impact_results": impact_results,
        "evidence_basis": prompt_decision_evidence(evidence_manifest),
        "consolidated_response_guidance": _prompt_response_guidance_summary(response_guidance),
        "active_scenarios": compact_rules(active_rules),
        "same_equipment_active_signals": compact_rules(related_rules),
        "related_signals": payload["related_signals"],
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
        "station_status": payload["station_status"],
    }
    if alert:
        retained_only = not any(rule.get("state") == "TRIGGER" for rule in active_rules)
        status_instruction = (("선택 센서의 경보 임계값은 현재 재초과되지 않았고 이전 경보가 유지 중입니다. 현재 경보와 경보 이력을 구분하되, 비영점 가스 농도나 모의 누출을 부정하지 마세요. "
                               if retained_only else "선택 센서와 관련 구역의 동시 경보를 공통 원인별 시나리오로 묶고, 상호 악화 가능성과 대응 우선순위를 종합하세요. ") +
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
        "경보 시 여러 임계값 조건을 각각 독립 사고로 나열하지 말고 공통 원인과 전개가 같은 발생 가능 시나리오로 종합하세요. "
        "consolidated_response_guidance는 서버가 최종 답변 뒤에 붙이는 단일 행동계획이므로 조치 문장을 반복하지 말고 현재 판단과 근거를 설명하세요. "
        + status_instruction +
        "evidence_basis.impact.calculation_status가 not_requested이면 피해영향 계산을 했다고 말하지 마세요. "
        "public_operating_envelope_screen은 공개 실험 운전범위의 설명용 비교이며 모델 정확도 판정이 아닙니다. flow_context의 의미를 바꾸거나 없는 유량을 만들지 마세요. "
        "runtime_calibration.status=active는 저장 뱅크 경계 보정이 적용되었다는 뜻일 뿐 차량·디스펜서·전체 충전루프 실측 검증을 뜻하지 않습니다. reference_defaults와 requested_unavailable은 기준값 실행으로 설명하세요. "
        "public accident action category counts는 대응계획의 근거 범위만 나타내며, 조치의 효과나 사고확률을 의미하지 않습니다. "
        "confidential_local_accident_response_coverage는 비식별 실제 사고 메타데이터의 대응계획 연결성만 나타내며, 사고 원문·효과성·확률·물리 검증으로 확대하지 마세요. "
        "실제 누출, 안전밸브 방출, 센서값 기준 가정 누출을 혼동하지 마세요. 계산된 피해영향 수치만 언급하고 안전거리를 확정하지 마세요. "
        "impact_results의 consequence_validation_scope가 COMPONENT_SCREENING_BOUNDED이면, 외부 비밀폐 자유제트의 구성요소 수준 표본 표시 근거와 실제 설비·감압·배치·충전소-차량 전체 루프·현장 안전거리 검증의 부재를 함께 설명하세요. "
        "사용자에게 HAZOP·DB·규칙 ID나 계산 엔진 제품명을 노출하지 마세요. "
        + ("한국어 Markdown으로 '현재 상태', '관련 구역의 경보·이력', '예방·안전관리' 순서로 답하세요. "
           if not alert else "한국어 Markdown으로 '현재 판정', '발생 가능 시나리오', '판단 근거와 피해영향' 순서로 간결하게 답하세요. 단계별 대응과 예방관리는 서버의 통합 행동계획에서 제시합니다. ") +
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
    answer, llm_claim_guard = guard_llm_claims(answer, evidence_manifest)
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
    if response_markdown:
        answer = (answer or "선택 센서의 상태를 확인했습니다.").rstrip() + "\n\n---\n\n" + response_markdown
    return {"sensor_id": sensor_id, "time_s": payload["time_s"],
            "answer": answer or "선택 센서의 상태를 확인했습니다.",
            "model": reply.get("model", ""), "impact_results": impact_results,
            "active_rule_count": len(active_rules), "related_active_count": len(related_rules),
            "sensor_status": payload["sensor_status"],
            "evidence_manifest": evidence_manifest,
            "response_guidance": response_guidance,
            "llm_claim_guard": llm_claim_guard}


@app.post("/api/simulations/{job_id}/sensors/{sensor_id}/analyze/stream")
async def analyze_simulation_sensor_stream(job_id: str, sensor_id: str,
                                           request: SensorAnalysisInput) -> StreamingResponse:
    return _stream_analysis_response(
        lambda: analyze_simulation_sensor(job_id, sensor_id, request),
        "선택 센서와 관련 설비 신호를 분석하고 있습니다…",
    )


@app.post("/api/simulations/{job_id}/sensors/{sensor_id}/analyze/direct")
async def analyze_simulation_sensor_direct(job_id: str, sensor_id: str,
                                           request: SensorAnalysisInput) -> dict[str, Any]:
    """Selected-sensor one-pass LLM answer without the RAG/review pipeline."""
    return await analyze_simulation_sensor(job_id, sensor_id,
                                           request.model_copy(update={"direct": True, "one_pass": True}))


@app.post("/api/simulations/{job_id}/sensors/{sensor_id}/analyze/direct/stream")
async def analyze_simulation_sensor_direct_stream(job_id: str, sensor_id: str,
                                                  request: SensorAnalysisInput) -> StreamingResponse:
    return _stream_analysis_response(
        lambda: analyze_simulation_sensor_direct(job_id, sensor_id, request),
        "선택 센서와 관련 설비 신호를 확인하고 있습니다…",
    )


@app.post("/api/simulations/{job_id}/assistants/sensors/{sensor_id}")
async def selected_sensor_assistant(job_id: str, sensor_id: str,
                                    request: SensorAssistantInput) -> dict[str, Any]:
    """Selected-sensor assistant boundary with no main-chat history or RAG modes."""
    internal = SensorAnalysisInput(
        provider=request.provider, question=request.question, time_s=request.time_s,
        direct=True, one_pass=True, language=request.language,
    )
    return await analyze_simulation_sensor(job_id, sensor_id, internal)


@app.post("/api/simulations/{job_id}/assistants/sensors/{sensor_id}/stream")
async def selected_sensor_assistant_stream(job_id: str, sensor_id: str,
                                           request: SensorAssistantInput) -> StreamingResponse:
    return _stream_analysis_response(
        lambda: selected_sensor_assistant(job_id, sensor_id, request),
        "선택 센서와 관련 설비 신호를 확인하고 있습니다…",
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
