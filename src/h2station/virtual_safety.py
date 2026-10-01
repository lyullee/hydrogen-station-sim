"""Simulation-only emergency actuators, feedback, and training records.

Commands are intentionally distinct from measured actuator state.  This module
never addresses a plant PLC; it only changes the station's virtual flow paths.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from math import cos, exp, radians, sqrt
from threading import RLock
from typing import Any, Mapping
from uuid import uuid4

from .safety_runtime import FaultEvent, FaultKind


BANKS = ("low", "medium", "high")
ZONES = ("unloading", "compressor", "storage", "dispenser")
VALVE_LABELS = {
    "trailer.source": "트레일러 측 공급 차단",
    "trailer.station": "충전소 측 하역 차단",
    "compressor.suction": "압축기 흡입 차단",
    "compressor.discharge": "압축기 토출 차단",
    **{f"bank.{bank}.inlet": f"{bank} 저장뱅크 유입 차단" for bank in BANKS},
    **{f"bank.{bank}.outlet": f"{bank} 저장뱅크 유출 차단" for bank in BANKS},
    "dispenser.1": "차량 1 충전라인 차단",
    "dispenser.2": "차량 2 충전라인 차단",
    **{f"vent.{bank}": f"{bank} 뱅크 설계 벤트" for bank in BANKS},
}
FAULTS = ("none", "stuck_open", "stuck_closed", "seat_leak", "feedback_fault")
RECOVERY_CHECKS = (
    "source_removed", "leak_repaired", "tightness_test", "detector_test",
    "valve_test", "purge_complete", "pressure_test", "supervisor_approval",
)


@dataclass
class VirtualActuator:
    name: str
    commanded_open: bool
    actual_open: bool
    feedback_open: bool
    fault: str = "none"
    due_s: float | None = None
    flow_check_s: float | None = None
    status: str = "ready"
    action_id: str | None = None

    def flow_fraction(self) -> float:
        if self.actual_open:
            return 1.0
        return 0.03 if self.fault == "seat_leak" else 0.0

    def snapshot(self) -> dict[str, Any]:
        return {"label": VALVE_LABELS[self.name], "commanded_open": self.commanded_open,
                "actual_open": self.actual_open, "feedback_open": self.feedback_open,
                "flow_fraction": self.flow_fraction(), "fault": self.fault,
                "due_s": self.due_s, "status": self.status}


class VirtualSafetyRuntime:
    """Actuator commands, virtual personnel, recovery gates, and replay history."""

    def __init__(self) -> None:
        self._lock = RLock()
        self.valves = {name: VirtualActuator(name, not name.startswith("vent."),
                                             not name.startswith("vent."),
                                             not name.startswith("vent."))
                       for name in VALVE_LABELS}
        self.line_pressure_mpa = {name: None for name in VALVE_LABELS if not name.startswith("vent.")}
        self.ventilation = {zone: {"commanded": True, "running": True, "fault": False}
                            for zone in ZONES}
        self.cooling = {bank: {"commanded": False, "running": False, "fault": False}
                        for bank in BANKS}
        self.power_isolated = {zone: False for zone in ZONES}
        self.access_restricted = {zone: False for zone in ZONES}
        self.personnel = {"unloading": 1, "compressor": 1, "storage": 2, "dispenser": 2}
        self.evacuated = {zone: 0 for zone in ZONES}
        self.vehicles = {"trailer": 1, "vehicle_1": 1, "vehicle_2": 1}
        self.vehicles_evacuated = {name: 0 for name in self.vehicles}
        self.wind_direction_deg = 0.0
        self.wind_speed_m_s = 3.0
        self.esd_requested = False
        self.responders_notified = False
        self.recovery = {check: False for check in RECOVERY_CHECKS}
        self.recovery_approved = False
        self.purge_due_s: float | None = None
        self.purge_start_s: float | None = None
        self.purge_bank: str | None = None
        self.purge_h2_fraction = {bank: 1.0 for bank in BANKS}
        self.inert_purge_available = True
        self.diagnostic: dict[str, Any] | None = None
        self._hazard_ids: set[str] = set()
        self.actions: list[dict[str, Any]] = []
        self._pending_metric_actions: dict[str, dict[str, Any]] = {}
        self.latest_time_s = 0.0

    def allows(self, name: str) -> bool:
        with self._lock:
            return self.valves[name].flow_fraction() > 0.0

    def opening(self, name: str) -> float:
        with self._lock:
            return self.valves[name].flow_fraction()

    def issue(self, kind: str, target: str, time_s: float, *,
              process=None, note: str = "", baseline_metrics: Mapping[str, Any] | None = None) -> dict[str, Any]:
        with self._lock:
            if not 0 <= time_s or time_s + 1e-6 < self.latest_time_s:
                raise ValueError("Action time must follow the simulation clock")
            action = {"id": uuid4().hex[:12], "kind": kind, "target": target,
                      "issued_s": time_s, "completed_s": None,
                      "status": "commanded", "note": note[:240],
                      "before": None, "after": None,
                      "baseline_metrics": deepcopy(dict(baseline_metrics or {})),
                      "after_metrics": None}
            if kind in ("valve.close", "valve.open", "vent.close", "vent.open"):
                if target not in self.valves:
                    raise ValueError("Unknown virtual valve")
                if kind.startswith("vent.") != target.startswith("vent."):
                    raise ValueError("Vent commands require a vent target")
                valve = self.valves[target]
                action["before"] = valve.snapshot()
                valve.commanded_open = kind.endswith(".open")
                valve.due_s = time_s + (0.6 if target.startswith("vent.") else 0.4)
                valve.flow_check_s = None
                valve.status = "moving"
                valve.action_id = action["id"]
            elif kind == "operation.stop":
                operations = ("trailer_supply", "pressure_recharge", "vehicle_1", "vehicle_2")
                if target not in (*operations, "all") or process is None:
                    raise ValueError("Unknown process operation")
                action["before"] = process.snapshot()["settings"]
                for operation in operations if target == "all" else (target,):
                    process.stop(operation, "safety-action")
                self._finish(action, time_s, "confirmed", process.snapshot()["settings"])
            elif kind == "esd.trip":
                self.esd_requested = True
                self._finish(action, time_s, "confirmed", {"esd_requested": True})
            elif kind in ("ventilation.on", "ventilation.off", "cooling.on", "cooling.off"):
                group = self.ventilation if kind.startswith("ventilation") else self.cooling
                if target not in group:
                    raise ValueError("Unknown auxiliary equipment")
                action["before"] = dict(group[target])
                group[target]["commanded"] = kind.endswith(".on")
                group[target]["running"] = group[target]["commanded"] and not group[target]["fault"]
                self._finish(action, time_s,
                             "failed" if group[target]["commanded"] != group[target]["running"] else "confirmed",
                             dict(group[target]))
            elif kind in ("power.isolate", "power.restore"):
                if target not in ZONES:
                    raise ValueError("Unknown power zone")
                action["before"] = self.power_isolated[target]
                self.power_isolated[target] = kind == "power.isolate"
                self._finish(action, time_s, "confirmed", self.power_isolated[target])
            elif kind in ("access.restrict", "access.release"):
                if target not in ZONES:
                    raise ValueError("Unknown access zone")
                action["before"] = self.access_restricted[target]
                self.access_restricted[target] = kind == "access.restrict"
                self._finish(action, time_s, "confirmed", self.access_restricted[target])
            elif kind == "personnel.evacuate":
                if target not in ZONES:
                    raise ValueError("Unknown evacuation zone")
                action["before"] = self.personnel[target]
                self.evacuated[target] += self.personnel[target]
                self.personnel[target] = 0
                self.access_restricted[target] = True
                self._finish(action, time_s, "confirmed", {"remaining": 0,
                                                            "evacuated": self.evacuated[target]})
            elif kind == "vehicle.evacuate":
                if target not in self.vehicles or process is None:
                    raise ValueError("Unknown virtual vehicle")
                operation = "trailer_supply" if target == "trailer" else target
                if process.settings[operation] or (target == "trailer" and process.settings["pressure_recharge"]):
                    raise ValueError("Stop the connected transfer before moving the vehicle")
                required = (("trailer.source", "trailer.station") if target == "trailer"
                            else ("dispenser." + target[-1],))
                if any(self.valves[name].status != "confirmed" or
                       self.valves[name].actual_open or self.valves[name].feedback_open or
                       self.valves[name].flow_fraction() > 0 for name in required):
                    raise ValueError("Confirm vehicle-side isolation and zero residual flow first")
                zone = "unloading" if target == "trailer" else "dispenser"
                action["before"] = self.vehicles[target]
                self.vehicles_evacuated[target] += self.vehicles[target]
                self.vehicles[target] = 0
                self.access_restricted[zone] = True
                self._finish(action, time_s, "confirmed", {"remaining": 0, "evacuated": self.vehicles_evacuated[target]})
            elif kind == "responders.notify":
                self.responders_notified = True
                self._finish(action, time_s, "confirmed", {"virtual_notification": True})
            elif kind == "recovery.record":
                if target not in self.recovery:
                    raise ValueError("Unknown recovery check")
                if target in ("purge_complete", "tightness_test", "detector_test",
                              "valve_test", "pressure_test"):
                    raise ValueError("Run the corresponding virtual test or purge procedure")
                if target == "supervisor_approval" and not all(self.recovery[key] for key in
                    RECOVERY_CHECKS if key != "supervisor_approval"):
                    raise ValueError("Complete technical recovery checks before supervisor approval")
                self.recovery[target] = True
                self._finish(action, time_s, "confirmed", {"check": target, "passed": True})
            elif kind in ("tightness.test", "detector.test", "valve.test", "pressure.test"):
                if self.diagnostic is not None:
                    raise ValueError("Another virtual diagnostic test is in progress")
                if kind in ("tightness.test", "pressure.test") and target not in BANKS:
                    raise ValueError("Select a storage bank for the line test")
                if kind in ("tightness.test", "pressure.test") and any(
                    self.valves[f"bank.{target}.{side}"].flow_fraction() > 0
                    for side in ("inlet", "outlet")):
                    raise ValueError("Isolate the tested bank line before starting")
                if kind == "tightness.test" and not (
                    self.recovery["source_removed"] and self.recovery["leak_repaired"]):
                    raise ValueError("Remove the source and resolve the leak before tightness testing")
                if kind == "pressure.test" and not all(self.recovery[key] for key in
                    ("tightness_test", "valve_test", "purge_complete")):
                    raise ValueError("Tightness, valve, and purge checks must precede pressure testing")
                source = dict(baseline_metrics or {})
                self.diagnostic = {"kind": kind, "target": target, "action_id": action["id"],
                                   "start_s": time_s, "due_s": time_s + (3.0 if kind in
                                    ("tightness.test", "pressure.test") else 1.0),
                                   "initial_pressure_mpa": self.line_pressure_mpa.get(f"bank.{target}.outlet"),
                                   "test_pressure_mpa": min(float((source.get("bank_pressure_mpa") or {}).get(target) or 0),
                                                            {"low": 50, "medium": 70, "high": 100}.get(target, 0)),
                                   "detectors_good": bool(source.get("detectors_good")),
                                   "leak_flow_g_s": float(source.get("total_leak_flow_g_s") or 0)}
                action["after"] = {"test": kind, "target": target, "in_progress": True}
            elif kind == "purge.run":
                if target not in BANKS:
                    raise ValueError("Select a storage bank for the virtual purge")
                if not self.inert_purge_available:
                    raise ValueError("Inert purge source is unavailable")
                if any(self.valves[f"bank.{target}.{side}"].flow_fraction() > 0 or
                       self.valves[f"bank.{target}.{side}"].feedback_open
                       for side in ("inlet", "outlet")):
                    raise ValueError("Isolate the bank inlet and outlet before purging its line")
                if self.purge_due_s is not None:
                    raise ValueError("A virtual purge is already in progress")
                self.purge_due_s = time_s + 5.0
                self.purge_start_s = time_s
                self.purge_bank = target
                action["after"] = {"isolated_line": target, "inert_purge_running": True}
            elif kind == "repair.leak":
                self.recovery["leak_repaired"] = True
                self._finish(action, time_s, "confirmed", {"removed_fault_id": target})
            elif kind == "restart.approve":
                missing = [key for key, passed in self.recovery.items() if not passed]
                if missing:
                    raise ValueError("Recovery checks incomplete: " + ", ".join(missing))
                self.recovery_approved = True
                self.esd_requested = False
                self._finish(action, time_s, "confirmed", {"recovery_approved": True})
            else:
                raise ValueError("Unknown virtual safety action")
            self.actions.append(action)
            self._pending_metric_actions[action["id"]] = action
            return deepcopy(action)

    def record_metrics(self, time_s: float, metrics: Mapping[str, Any]) -> None:
        with self._lock:
            if self.diagnostic is not None:
                self.diagnostic["detectors_good"] = (self.diagnostic["detectors_good"] and
                                                     bool(metrics.get("detectors_good")))
                self.diagnostic["leak_flow_g_s"] = max(
                    self.diagnostic["leak_flow_g_s"],
                    float(metrics.get("total_leak_flow_g_s") or 0))
            for action_id, action in tuple(self._pending_metric_actions.items()):
                if action["completed_s"] is not None and time_s > action["completed_s"] + 1e-6:
                    action["after_metrics"] = deepcopy(dict(metrics))
                    del self._pending_metric_actions[action_id]

    def record_incident_resolution(self, fault_ids: list[str], time_s: float) -> dict[str, Any]:
        """Record the training-only removal of incident inputs after confirmed response."""
        with self._lock:
            action = {"id": uuid4().hex[:12], "kind": "incident.auto-resolve",
                      "target": "station", "issued_s": time_s, "completed_s": time_s,
                      "status": "confirmed",
                      "note": "ESD와 즉시 조치 확인 후 사고 입력 자동 종료",
                      "before": {"active_fault_ids": list(fault_ids)},
                      "after": {"ended_fault_ids": list(fault_ids)},
                      "baseline_metrics": {}, "after_metrics": None}
            self.actions.append(action)
            return deepcopy(action)

    def observe_hazards(self, active_faults: tuple[str, ...] | list[str]) -> None:
        """A newly introduced incident invalidates the preceding recovery approval."""
        with self._lock:
            current = {fault for fault in active_faults if not fault.startswith("relief-open:")}
            if current - self._hazard_ids:
                self.recovery = {check: False for check in RECOVERY_CHECKS}
                self.recovery_approved = False
                if self.diagnostic is not None:
                    action = next((row for row in reversed(self.actions)
                                   if row["id"] == self.diagnostic["action_id"]), None)
                    if action is not None:
                        self._finish(action, self.latest_time_s, "failed",
                                     {"reason": "New hazard interrupted virtual recovery test"})
                    self.diagnostic = None
            self._hazard_ids = current

    @staticmethod
    def _finish(action: dict[str, Any], time_s: float, status: str, after: Any) -> None:
        action["completed_s"] = time_s
        action["status"] = status
        action["after"] = deepcopy(after)

    def tick(self, time_s: float) -> None:
        with self._lock:
            self.latest_time_s = max(self.latest_time_s, time_s)
            if self.purge_due_s is not None:
                elapsed = max(0.0, time_s - self.purge_start_s)
                self.purge_h2_fraction[self.purge_bank] = max(.005, exp(-1.1 * elapsed))
            if self.purge_due_s is not None and time_s >= self.purge_due_s:
                self.purge_h2_fraction[self.purge_bank] = 0.005
                for side in ("inlet", "outlet"):
                    self.line_pressure_mpa[f"bank.{self.purge_bank}.{side}"] = .1
                self.recovery["purge_complete"] = True
                action = next((row for row in reversed(self.actions) if row["kind"] == "purge.run" and row["status"] == "commanded"), None)
                if action is not None:
                    self._finish(action, time_s, "confirmed",
                                 {"isolated_line": self.purge_bank,
                                  "virtual_h2_fraction": self.purge_h2_fraction[self.purge_bank]})
                self.purge_due_s = None
                self.purge_start_s = None
                self.purge_bank = None
            if self.diagnostic is not None:
                test = self.diagnostic
                progress = min(1.0, max(0.0, (time_s - test["start_s"]) /
                                        (test["due_s"] - test["start_s"])))
                if test["kind"] == "pressure.test":
                    step = .25 if progress < 1/3 else .5 if progress < 2/3 else 1.0
                    self.line_pressure_mpa[f"bank.{test['target']}.outlet"] = step * test["test_pressure_mpa"]
                if test["kind"] == "tightness.test" and any(
                    self.valves[f"bank.{test['target']}.{side}"].fault == "seat_leak"
                    for side in ("inlet", "outlet")):
                    self.line_pressure_mpa[f"bank.{test['target']}.outlet"] = (
                        test["initial_pressure_mpa"] or 0) * (1 - .1 * progress)
                if time_s >= test["due_s"]:
                    valve_good = all(valve.fault == "none" and
                                     valve.feedback_open == valve.actual_open and
                                     (valve.commanded_open or valve.flow_fraction() == 0)
                                     for valve in self.valves.values())
                    pass_test = {"tightness.test": lambda: test["leak_flow_g_s"] <= .01 and all(
                                     self.valves[f"bank.{test['target']}.{side}"].flow_fraction() == 0
                                     for side in ("inlet", "outlet")),
                                 "detector.test": lambda: test["detectors_good"],
                                 "valve.test": lambda: valve_good,
                                 "pressure.test": lambda: test["test_pressure_mpa"] > 0 and
                                                  test["leak_flow_g_s"] <= .01 and valve_good}[test["kind"]]()
                    check = {"tightness.test": "tightness_test", "detector.test": "detector_test",
                             "valve.test": "valve_test", "pressure.test": "pressure_test"}[test["kind"]]
                    self.recovery[check] = pass_test
                    action = next((row for row in reversed(self.actions) if row["id"] == test["action_id"]), None)
                    if action is not None:
                        self._finish(action, time_s, "confirmed" if pass_test else "failed",
                                     {"test": test["kind"], "passed": pass_test,
                                      "line_pressure_mpa": self.line_pressure_mpa.get(
                                          f"bank.{test['target']}.outlet")})
                    self.diagnostic = None
            for valve in self.valves.values():
                if valve.due_s is None or time_s < valve.due_s:
                    continue
                valve.due_s = None
                if valve.fault == "stuck_open":
                    valve.actual_open = True
                elif valve.fault == "stuck_closed":
                    valve.actual_open = False
                else:
                    valve.actual_open = valve.commanded_open
                valve.feedback_open = (not valve.actual_open if valve.fault == "feedback_fault"
                                       else valve.actual_open)
                failed = (valve.actual_open != valve.commanded_open or
                          valve.feedback_open != valve.actual_open or
                          (not valve.commanded_open and valve.flow_fraction() > 0))
                valve.status = "failed" if failed else "awaiting-flow" if not valve.commanded_open else "confirmed"
                valve.flow_check_s = time_s + 0.4 if valve.status == "awaiting-flow" else None
                action = next((row for row in reversed(self.actions) if row["id"] == valve.action_id), None)
                if action is not None and valve.status != "awaiting-flow":
                    self._finish(action, time_s, valve.status, valve.snapshot())

    def observe(self, time_s: float, *, recharge_bank: str | None,
                dispatch_banks: tuple[str | None, ...], compressor_flow_g_s: float,
                dispenser_flows_g_s: tuple[float, float],
                pcv_flows_g_s: tuple[float, float] = (0.0, 0.0),
                pressure_sources_mpa: Mapping[str, float] | None = None) -> None:
        """Confirm a closure from both position feedback and residual line flow."""
        with self._lock:
            for name, pressure in (pressure_sources_mpa or {}).items():
                if name in self.line_pressure_mpa and self.valves[name].flow_fraction() > 0:
                    self.line_pressure_mpa[name] = float(pressure)
            for name, valve in self.valves.items():
                if valve.status != "awaiting-flow":
                    continue
                if valve.flow_check_s is not None and time_s < valve.flow_check_s:
                    continue
                if name.startswith("bank."):
                    _, bank, side = name.split(".")
                    flow = compressor_flow_g_s if side == "inlet" and recharge_bank == bank else (
                        sum(pcv_flows_g_s[index] for index, selected in enumerate(dispatch_banks)
                            if selected == bank) if side == "outlet" else 0.0)
                elif name.startswith("dispenser."):
                    flow = dispenser_flows_g_s[int(name.rsplit(".", 1)[1]) - 1]
                elif name.startswith(("trailer.", "compressor.")):
                    flow = compressor_flow_g_s
                else:
                    flow = 0.0  # Vent flow is checked against its separate release telemetry.
                verified = not valve.feedback_open and flow < 0.01 and valve.flow_fraction() == 0
                valve.status = "confirmed" if verified else "failed"
                action = next((row for row in reversed(self.actions) if row["id"] == valve.action_id), None)
                if action is not None:
                    self._finish(action, time_s, valve.status,
                                 {**valve.snapshot(), "observed_flow_g_s": flow})

    def set_fault(self, device: str, fault: str, time_s: float) -> dict[str, Any]:
        with self._lock:
            if device in self.valves:
                if fault not in FAULTS:
                    raise ValueError("Invalid valve fault")
                valve = self.valves[device]
                valve.fault = fault
                if fault == "none":
                    valve.feedback_open = valve.actual_open
                elif fault == "feedback_fault":
                    valve.feedback_open = not valve.actual_open
                valve.status = "fault-injected" if fault != "none" else "ready"
            elif device.startswith("ventilation.") or device.startswith("cooling."):
                group_name, zone = device.split(".", 1)
                group = self.ventilation if group_name == "ventilation" else self.cooling
                if zone not in group or fault not in ("none", "failure"):
                    raise ValueError("Invalid auxiliary equipment fault")
                group[zone]["fault"] = fault == "failure"
                group[zone]["running"] = group[zone]["commanded"] and not group[zone]["fault"]
            else:
                raise ValueError("Unknown virtual device")
            record = {"id": uuid4().hex[:12], "kind": "fault.set", "target": device,
                      "issued_s": time_s, "completed_s": time_s, "status": "confirmed",
                      "note": fault, "before": None, "after": fault}
            self.actions.append(record)
            return deepcopy(record)

    def vent_events(self, time_s: float) -> tuple[FaultEvent, ...]:
        with self._lock:
            return tuple(FaultEvent(event_id=f"vent-{bank}", kind=FaultKind.HYDROGEN_LEAK,
                                    target=f"cascade.{bank}", start_time_s=time_s,
                                    leak_diameter_m=0.0005 * valve.flow_fraction(), rate_s=0.02)
                         for bank in BANKS if (valve := self.valves[f"vent.{bank}"]).flow_fraction() > 0)

    def cooling_events(self, time_s: float, ambient_k: float) -> tuple[FaultEvent, ...]:
        with self._lock:
            return tuple(FaultEvent(event_id=f"cooling-{bank}", kind=FaultKind.TEMPERATURE_DISTURBANCE,
                                    target=f"cascade.{bank}", start_time_s=time_s,
                                    external_temperature_k=ambient_k, heat_transfer_ua_w_k=1800.0)
                         for bank in BANKS if self.cooling[bank]["running"])

    def detector_multiplier(self, zone: str) -> float:
        with self._lock:
            group = ("storage" if zone.startswith("cascade") or zone in ("storage", "header")
                     else "compressor" if zone.startswith("compressor")
                     else "dispenser" if zone.startswith(("dispenser", "vehicle", "fueling"))
                     else "unloading")
            # A transparent, deliberately coarse virtual dispersion proxy;
            # it is not a CFD model or a detector-placement certification.
            ventilation = 0.4 if self.ventilation[group]["running"] else 1.3
            wind_speed = min(2.0, max(.5, sqrt(3.0 / max(.5, self.wind_speed_m_s))))
            direction = {"unloading": 270, "compressor": 180,
                         "storage": 90, "dispenser": 0}[group]
            exposure = 1.0 + .25 * cos(radians(self.wind_direction_deg - direction))
            return ventilation * wind_speed * exposure

    def snapshot(self, *, include_actions: bool = True) -> dict[str, Any]:
        with self._lock:
            return {"time_s": self.latest_time_s,
                    "valves": {name: valve.snapshot() for name, valve in self.valves.items()},
                    "line_pressure_mpa": dict(self.line_pressure_mpa),
                    "ventilation": deepcopy(self.ventilation), "cooling": deepcopy(self.cooling),
                    "power_isolated": dict(self.power_isolated),
                    "access_restricted": dict(self.access_restricted),
                    "personnel": dict(self.personnel), "evacuated": dict(self.evacuated),
                    "vehicles": dict(self.vehicles),
                    "vehicles_evacuated": dict(self.vehicles_evacuated),
                    "wind_direction_deg": self.wind_direction_deg,
                    "wind_speed_m_s": self.wind_speed_m_s,
                    "esd_requested": self.esd_requested,
                    "responders_notified": self.responders_notified,
                    "recovery": dict(self.recovery),
                    "recovery_approved": self.recovery_approved,
                    "purge_due_s": self.purge_due_s,
                    "purge_start_s": self.purge_start_s,
                    "purge_bank": self.purge_bank,
                    "purge_h2_fraction": dict(self.purge_h2_fraction),
                    "inert_purge_available": self.inert_purge_available,
                    "diagnostic": deepcopy(self.diagnostic),
                    "actions": deepcopy(self.actions[-300:]) if include_actions else []}


def suggested_actions(plan_id: str, node_id: str | None = None) -> list[dict[str, str]]:
    """Reviewed, executable templates used by HAZOP and LLM displays."""
    bank = {"N07": "low", "N08": "medium", "N09": "high"}.get(node_id or "")
    dispenser = "2" if node_id in ("N15", "N16", "N17", "N18") else "1"
    zone = ("storage" if bank or node_id in ("N10", "N22") else
            "unloading" if node_id in ("N01", "N02") else
            "compressor" if node_id in ("N03", "N04", "N05", "N06", "N21") else "dispenser")
    actions: list[tuple[str, str, str]] = []
    if plan_id in ("gas_release", "hydrogen_fire", "external_fire", "overpressure",
                   "relief_discharge", "isolation_failure"):
        actions.append(("operation.stop", "all", "충전·공급·압축 정지"))
        if bank:
            actions.extend((("valve.close", f"bank.{bank}.inlet", "해당 뱅크 유입 차단"),
                            ("valve.close", f"bank.{bank}.outlet", "해당 뱅크 유출 차단")))
        elif node_id in ("N01", "N02"):
            actions.extend((("valve.close", "trailer.source", "트레일러 측 차단"),
                            ("valve.close", "trailer.station", "충전소 하역 측 차단")))
        elif node_id in ("N03", "N04", "N05", "N06", "N21"):
            actions.extend((("valve.close", "compressor.suction", "압축기 흡입 차단"),
                            ("valve.close", "compressor.discharge", "압축기 토출 차단")))
        elif node_id in ("N11", "N12", "N13", "N14", "N15", "N16", "N17", "N18", "N19", "N23"):
            actions.append(("valve.close", f"dispenser.{dispenser}", f"충전기 {dispenser} 차단"))
        elif node_id in ("N10", "N22"):
            actions.extend(("valve.close", f"bank.{name}.outlet", f"{name} 뱅크 토출 차단")
                           for name in BANKS)
        actions.append(("access.restrict", zone, "영향 구역 출입 통제"))
        actions.append(("personnel.evacuate", zone, "영향 구역 인원 대피"))
        if plan_id in ("hydrogen_fire", "external_fire"):
            actions.append(("power.isolate", zone, "해당 구역 점화원·전원 격리"))
    elif plan_id in ("fueling_fault", "hose_connection", "precooling_fault"):
        actions.extend((("operation.stop", f"vehicle_{dispenser}", "해당 차량 충전 중지"),
                        ("valve.close", f"dispenser.{dispenser}", "해당 충전라인 차단")))
    elif plan_id in ("compressor_thermal", "low_supply_or_blockage", "flow_anomaly", "supply_connection"):
        actions.extend((("operation.stop", "pressure_recharge", "압력 보완 정지"),
                        ("valve.close", "compressor.discharge", "압축기 토출 차단")))
    elif plan_id == "vent_fault":
        actions.append(("operation.stop", "pressure_recharge", "재충전 중지"))
    elif plan_id == "sensor_fault":
        actions.append(("operation.stop", "all", "계측 확인까지 운전 보류"))
    if zone == "dispenser" and plan_id in ("fueling_fault", "hose_connection", "gas_release"):
        actions.append(("vehicle.evacuate", f"vehicle_{dispenser}",
                        f"차량 {dispenser} 연결 해제·차단 확인 후 대피"))
    if zone == "unloading" and plan_id in ("supply_connection", "gas_release", "external_fire"):
        actions.append(("vehicle.evacuate", "trailer", "트레일러 양단 차단 확인 후 대피"))
    if plan_id in ("hydrogen_fire", "external_fire") and bank:
        actions.append(("cooling.on", bank, "인접 용기 가상 냉각 가동"))
    if plan_id == "gas_release":
        actions.append(("ventilation.on", zone, "해당 구역 환기 가동"))
    return [{"kind": kind, "target": target, "label": label} for kind, target, label in actions]
