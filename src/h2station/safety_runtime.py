"""Sampled safety PLC, fault injection, and latched shutdown decisions."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
from typing import Mapping

import numpy as np

from .protocol import FuelingPhase


class FaultKind(str, Enum):
    SENSOR_BIAS = "sensor-bias"
    SENSOR_FREEZE = "sensor-freeze"
    PCV_STUCK_OPEN = "pcv-stuck-open"
    PCV_STUCK_CLOSED = "pcv-stuck-closed"
    CASCADE_VALVE_STUCK_OPEN = "cascade-valve-stuck-open"
    CASCADE_VALVE_STUCK_CLOSED = "cascade-valve-stuck-closed"
    PRECOOLER_LOSS = "precooler-loss"
    COMPRESSOR_TRIP = "compressor-trip"
    HYDROGEN_LEAK = "hydrogen-leak"
    EMERGENCY_STOP = "emergency-stop"
    PRESSURE_DISTURBANCE = "pressure-disturbance"
    TEMPERATURE_DISTURBANCE = "temperature-disturbance"
    EXTERNAL_FIRE = "external-fire"
    PIPE_RESTRICTION = "pipe-restriction"
    CHECK_VALVE_FAILURE = "check-valve-failure"


@dataclass(frozen=True)
class FaultEvent:
    event_id: str
    kind: FaultKind
    target: str
    start_time_s: float
    end_time_s: float | None = None
    magnitude: float = 0.0
    leak_diameter_m: float | None = None
    indoor: bool = False
    rate_s: float = 30.0
    external_temperature_k: float | None = None
    heat_transfer_ua_w_k: float = 0.0

    def __post_init__(self) -> None:
        if not self.event_id or not self.target:
            raise ValueError("Fault event_id and target are required")
        if self.start_time_s < 0.0:
            raise ValueError("Fault start time cannot be negative")
        if self.end_time_s is not None and self.end_time_s <= self.start_time_s:
            raise ValueError("Fault end time must be later than start time")
        if self.kind is FaultKind.HYDROGEN_LEAK:
            if self.leak_diameter_m is None or self.leak_diameter_m <= 0.0:
                raise ValueError("Hydrogen leaks require a positive leak diameter")
        if self.rate_s <= 0.0:
            raise ValueError("Fault response rate must be positive")
        if self.kind is FaultKind.EXTERNAL_FIRE:
            if self.external_temperature_k is None or self.external_temperature_k <= 273.15:
                raise ValueError("External fires require a source temperature above 0 C")
            if self.heat_transfer_ua_w_k <= 0.0:
                raise ValueError("External fires require a positive heat-transfer UA")
        if self.kind is FaultKind.TEMPERATURE_DISTURBANCE and self.external_temperature_k is None:
            raise ValueError("Temperature disturbances require an external temperature")
        if self.kind is FaultKind.PIPE_RESTRICTION and not 0.0 <= self.magnitude <= 1.0:
            raise ValueError("Pipe restriction magnitude is an open-area multiplier from 0 to 1")

    def active_at(self, time_s: float) -> bool:
        return time_s >= self.start_time_s and (
            self.end_time_s is None or time_s < self.end_time_s
        )


class FaultSchedule:
    def __init__(self, events: tuple[FaultEvent, ...] = ()) -> None:
        if len({event.event_id for event in events}) != len(events):
            raise ValueError("Fault event IDs must be unique")
        self.events = tuple(sorted(events, key=lambda event: event.start_time_s))

    def active_events(self, time_s: float) -> tuple[FaultEvent, ...]:
        return tuple(event for event in self.events if event.active_at(time_s))


@dataclass(frozen=True)
class StationMeasurements:
    time_s: float
    fueling_phase: FuelingPhase
    vehicle_pressure_pa: float
    vehicle_temperature_k: float
    hose_pressure_pa: float
    hose_temperature_k: float
    pcv_mass_flow_kg_s: float
    nozzle_mass_flow_kg_s: float
    precooler_outlet_temperature_k: float
    hydrogen_concentration_by_detector: Mapping[str, float]


@dataclass(frozen=True)
class OperationalOverride:
    forced_pcv_opening: float | None = None
    forced_cascade_valve_opening: float | None = None
    precooler_capacity_multiplier: float = 1.0
    compressor_enabled: bool = True
    emergency_stop_requested: bool = False
    active_leaks: tuple[FaultEvent, ...] = ()
    pipe_restrictions: Mapping[str, float] = ()
    check_valve_failures: tuple[str, ...] = ()


class FaultInjector:
    """Apply deterministic fault events without embedding them in physical models."""

    _MEASUREMENT_FIELDS = {
        "vehicle_pressure_pa",
        "vehicle_temperature_k",
        "hose_pressure_pa",
        "hose_temperature_k",
        "pcv_mass_flow_kg_s",
        "nozzle_mass_flow_kg_s",
        "precooler_outlet_temperature_k",
    }

    def __init__(self, schedule: FaultSchedule) -> None:
        self.schedule = schedule
        self._frozen_values: dict[tuple[str, str], float] = {}

    def reset(self) -> None:
        self._frozen_values.clear()

    def measurements(self, raw: StationMeasurements) -> StationMeasurements:
        changes: dict[str, float] = {}
        for event in self.schedule.active_events(raw.time_s):
            if event.target not in self._MEASUREMENT_FIELDS:
                continue
            if event.kind is FaultKind.SENSOR_BIAS:
                changes[event.target] = float(
                    getattr(raw, event.target) + event.magnitude
                )
            elif event.kind is FaultKind.SENSOR_FREEZE:
                key = (event.event_id, event.target)
                self._frozen_values.setdefault(key, float(getattr(raw, event.target)))
                changes[event.target] = self._frozen_values[key]
        return replace(raw, **changes) if changes else raw

    def operational_override(self, time_s: float) -> OperationalOverride:
        pcv_opening: float | None = None
        cascade_opening: float | None = None
        precooler_multiplier = 1.0
        compressor_enabled = True
        emergency_stop = False
        leaks: list[FaultEvent] = []
        restrictions: dict[str, float] = {}
        check_valves: list[str] = []
        for event in self.schedule.active_events(time_s):
            if event.kind is FaultKind.PCV_STUCK_OPEN:
                pcv_opening = 1.0
            elif event.kind is FaultKind.PCV_STUCK_CLOSED:
                pcv_opening = 0.0
            elif event.kind is FaultKind.CASCADE_VALVE_STUCK_OPEN:
                cascade_opening = 1.0
            elif event.kind is FaultKind.CASCADE_VALVE_STUCK_CLOSED:
                cascade_opening = 0.0
            elif event.kind is FaultKind.PRECOOLER_LOSS:
                precooler_multiplier = max(0.0, min(1.0, event.magnitude))
            elif event.kind is FaultKind.COMPRESSOR_TRIP:
                compressor_enabled = False
            elif event.kind is FaultKind.EMERGENCY_STOP:
                emergency_stop = True
            elif event.kind is FaultKind.HYDROGEN_LEAK:
                leaks.append(event)
            elif event.kind is FaultKind.PIPE_RESTRICTION:
                restrictions[event.target] = min(restrictions.get(event.target, 1.0), event.magnitude)
            elif event.kind is FaultKind.CHECK_VALVE_FAILURE:
                check_valves.append(event.target)
        return OperationalOverride(
            forced_pcv_opening=pcv_opening,
            forced_cascade_valve_opening=cascade_opening,
            precooler_capacity_multiplier=precooler_multiplier,
            compressor_enabled=compressor_enabled,
            emergency_stop_requested=emergency_stop,
            active_leaks=tuple(leaks),
            pipe_restrictions=restrictions,
            check_valve_failures=tuple(check_valves),
        )


@dataclass(frozen=True)
class SafetyLimits:
    maximum_vehicle_pressure_pa: float
    maximum_vehicle_temperature_k: float
    maximum_precooler_outlet_temperature_k: float
    maximum_flow_imbalance_kg_s: float
    detector_alarm_volume_fraction: float
    detector_trip_volume_fraction: float
    trip_persistence_s: float

    def __post_init__(self) -> None:
        positive = (
            self.maximum_vehicle_pressure_pa,
            self.maximum_vehicle_temperature_k,
            self.maximum_precooler_outlet_temperature_k,
            self.maximum_flow_imbalance_kg_s,
            self.detector_alarm_volume_fraction,
            self.detector_trip_volume_fraction,
        )
        if any(value <= 0.0 for value in positive):
            raise ValueError("Safety limits must be positive")
        if self.detector_alarm_volume_fraction >= self.detector_trip_volume_fraction:
            raise ValueError("Detector alarm threshold must be below trip threshold")
        if self.trip_persistence_s < 0.0:
            raise ValueError("trip_persistence_s cannot be negative")


@dataclass(frozen=True)
class SafetyCommand:
    esd_latched: bool
    alarm_active: bool
    isolate_hydrogen_supply: bool
    close_pcv: bool
    close_cascade_valves: bool
    stop_compressor: bool
    keep_monitoring_energized: bool
    trip_causes: tuple[str, ...]


class SafetyPLC:
    """Independent, sampled, manually reset latched emergency-shutdown logic."""

    def __init__(self, limits: SafetyLimits) -> None:
        self.limits = limits
        self._esd_latched = False
        self._latched_causes: set[str] = set()
        self._condition_timers_s: dict[str, float] = {}

    def update(
        self,
        measurements: StationMeasurements,
        sample_period_s: float,
        emergency_stop_requested: bool = False,
    ) -> SafetyCommand:
        if sample_period_s <= 0.0:
            raise ValueError("sample_period_s must be positive")
        conditions = self._trip_conditions(measurements)
        conditions["manual-emergency-stop"] = emergency_stop_requested
        if emergency_stop_requested:
            self._esd_latched = True
            self._latched_causes.add("manual-emergency-stop")
        for cause, active in conditions.items():
            self._condition_timers_s[cause] = (
                self._condition_timers_s.get(cause, 0.0) + sample_period_s
                if active else 0.0
            )
            if active and self._condition_timers_s[cause] >= self.limits.trip_persistence_s:
                self._esd_latched = True
                self._latched_causes.add(cause)

        maximum_concentration = max(
            measurements.hydrogen_concentration_by_detector.values(),
            default=0.0,
        )
        alarm = (
            self._esd_latched
            or maximum_concentration >= self.limits.detector_alarm_volume_fraction
        )
        return SafetyCommand(
            esd_latched=self._esd_latched,
            alarm_active=alarm,
            isolate_hydrogen_supply=self._esd_latched,
            close_pcv=self._esd_latched,
            close_cascade_valves=self._esd_latched,
            stop_compressor=self._esd_latched,
            keep_monitoring_energized=True,
            trip_causes=tuple(sorted(self._latched_causes)),
        )

    def manual_reset(
        self,
        measurements: StationMeasurements,
        reset_requested: bool,
    ) -> bool:
        if not reset_requested or any(self._trip_conditions(measurements).values()):
            return False
        self._esd_latched = False
        self._latched_causes.clear()
        self._condition_timers_s.clear()
        return True

    def _trip_conditions(self, measurements: StationMeasurements) -> dict[str, bool]:
        numeric_values = (
            measurements.vehicle_pressure_pa,
            measurements.vehicle_temperature_k,
            measurements.hose_pressure_pa,
            measurements.hose_temperature_k,
            measurements.pcv_mass_flow_kg_s,
            measurements.nozzle_mass_flow_kg_s,
            measurements.precooler_outlet_temperature_k,
        )
        invalid_sensor = not all(np.isfinite(value) for value in numeric_values)
        maximum_concentration = max(
            measurements.hydrogen_concentration_by_detector.values(),
            default=0.0,
        )
        filling = measurements.fueling_phase is FuelingPhase.FILLING
        return {
            "invalid-critical-sensor": invalid_sensor,
            "vehicle-overpressure": (
                measurements.vehicle_pressure_pa >= self.limits.maximum_vehicle_pressure_pa
            ),
            "vehicle-overtemperature": (
                measurements.vehicle_temperature_k
                >= self.limits.maximum_vehicle_temperature_k
            ),
            "precooling-temperature-high": (
                filling
                and measurements.precooler_outlet_temperature_k
                >= self.limits.maximum_precooler_outlet_temperature_k
            ),
            "flow-imbalance": (
                filling
                and abs(
                    measurements.pcv_mass_flow_kg_s
                    - measurements.nozzle_mass_flow_kg_s
                ) >= self.limits.maximum_flow_imbalance_kg_s
            ),
            "hydrogen-detection-high": (
                maximum_concentration >= self.limits.detector_trip_volume_fraction
            ),
        }
