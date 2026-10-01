"""Operator-requested process modes and sampled relief valves."""

from __future__ import annotations

from copy import deepcopy
from threading import RLock
from typing import Any, Mapping

from .dispenser import SupplyState
from .safety_runtime import FaultEvent, FaultKind
from .tabulated import PropsSI
from .virtual_safety import VirtualSafetyRuntime


RELIEF_TARGETS = {
    "low": "cascade.low", "medium": "cascade.medium", "high": "cascade.high",
    "hose_1": "dispenser.hose", "hose_2": "dispenser_2.hose",
    "vehicle_1": "vehicle.tank", "vehicle_2": "vehicle_2.tank",
}


class ProcessRuntime:
    """Hold source inventory and requests across continuous solver windows.

    The trailer is an isothermal finite inventory, sampled at the controller rate.
    Its pressure is held over each BDF interval and updated from the integrated
    compressor transfer at the end of that interval.
    """

    def __init__(self, settings: Mapping[str, Any]) -> None:
        self._lock = RLock()
        self.settings = deepcopy(dict(settings))
        self.trailer_mass_kg = float(settings["trailer_capacity_kg"])
        self.trailer_temperature_k = float(settings["trailer_temperature_c"]) + 273.15
        density = float(PropsSI("Dmass", "P", float(settings["trailer_pressure_mpa"]) * 1e6,
                                "T", self.trailer_temperature_k, "Hydrogen"))
        self.trailer_volume_m3 = self.trailer_mass_kg / density
        self._trailer_pressure_pa = float(settings["trailer_pressure_mpa"]) * 1e6
        self.trailer_transferred_kg = 0.0
        self.recharge_transferred_kg = 0.0
        self.relief_open = {key: False for key in RELIEF_TARGETS}
        self.safety = VirtualSafetyRuntime()
        self.revision = 0
        self.stop_reason: dict[str, str | None] = {
            key: None for key in ("trailer_supply", "pressure_recharge", "vehicle_1", "vehicle_2")
        }

    def configure(self, settings: Mapping[str, Any]) -> None:
        with self._lock:
            updated = deepcopy(dict(settings))
            for field in ("trailer_capacity_kg", "trailer_pressure_mpa", "trailer_temperature_c"):
                if updated[field] != self.settings[field]:
                    raise ValueError(f"{field} can only change when a new simulation starts")
            if not self.safety.vehicles["trailer"] and (updated["trailer_supply"] or updated["pressure_recharge"]):
                raise ValueError("The trailer has departed; start a new simulation before transfer")
            for vehicle in ("vehicle_1", "vehicle_2"):
                if not self.safety.vehicles[vehicle] and updated[vehicle]:
                    raise ValueError(f"{vehicle} has departed; start a new simulation before refueling")
            for key, counter in (("trailer_supply", "trailer_transferred_kg"),
                                 ("pressure_recharge", "recharge_transferred_kg")):
                if updated[key] and not self.settings[key]:
                    setattr(self, counter, 0.0)
            for key in self.stop_reason:
                if updated[key] and not self.settings[key]:
                    self.stop_reason[key] = None
                elif not updated[key] and self.settings[key]:
                    self.stop_reason[key] = "operator"
            self.settings = updated
            self.revision += 1

    def stop(self, operation: str, reason: str = "controller") -> None:
        with self._lock:
            if self.settings[operation]:
                self.settings[operation] = False
                self.stop_reason[operation] = reason
                self.revision += 1

    def requested(self, operation: str) -> bool:
        with self._lock:
            return bool(self.settings[operation])

    def any_requested(self) -> bool:
        with self._lock:
            return any(self.settings[key] for key in
                       ("trailer_supply", "pressure_recharge", "vehicle_1", "vehicle_2"))

    def trailer_state(self) -> SupplyState:
        with self._lock:
            return SupplyState(self._trailer_pressure_pa, self.trailer_temperature_k)

    def source_available(self) -> bool:
        with self._lock:
            return (self.settings["trailer_supply"] and self.settings["pressure_recharge"]
                    and self.trailer_mass_kg > 0.1 and self.trailer_state().pressure_pa >= 2e6)

    def account_compressor(self, mass_flow_kg_s: float, duration_s: float) -> None:
        with self._lock:
            amount = max(0.0, mass_flow_kg_s * duration_s)
            amount = min(amount, max(self.trailer_mass_kg - 0.1, 0.0))
            self.trailer_mass_kg -= amount
            if amount:
                # Invert the supported P,T density table for this fixed-volume,
                # isothermal source. Recompute only at controller samples.
                density = self.trailer_mass_kg / self.trailer_volume_m3
                lower, upper = 1e5, float(self.settings["trailer_pressure_mpa"]) * 1e6
                for _ in range(25):
                    middle = (lower + upper) / 2
                    middle_density = PropsSI("Dmass", "P", middle, "T", self.trailer_temperature_k, "Hydrogen")
                    if middle_density < density:
                        lower = middle
                    else:
                        upper = middle
                self._trailer_pressure_pa = (lower + upper) / 2
            self.trailer_transferred_kg += amount
            self.recharge_transferred_kg += amount
            if self.trailer_mass_kg <= 0.1 or self._trailer_pressure_pa < 2e6:
                self.stop("trailer_supply", "source-depleted")
                self.stop("pressure_recharge", "source-depleted")

    def recharge_targets_pa(self) -> tuple[float, float, float]:
        with self._lock:
            return tuple(self.settings[f"recharge_target_{name}_mpa"] * 1e6
                         for name in ("low", "medium", "high"))

    def recharge_restart_margins_pa(self) -> tuple[float, float, float]:
        with self._lock:
            return tuple(self.settings[f"recharge_restart_margin_{name}_mpa"] * 1e6
                         for name in ("low", "medium", "high"))

    def stop_recharge_at_targets(self, pressures_pa: tuple[float, float, float]) -> None:
        with self._lock:
            if (self.settings["recharge_auto_stop"] and
                    all(pressure >= target
                        for pressure, target in zip(pressures_pa, self.recharge_targets_pa()))):
                self.stop("pressure_recharge", "bank-target")
                self.stop("trailer_supply", "bank-target")

    def relief_events(self, pressures_pa: Mapping[str, float], time_s: float) -> tuple[FaultEvent, ...]:
        events = []
        with self._lock:
            for key, target in RELIEF_TARGETS.items():
                setting = self.settings["relief_valves"][key]
                pressure = pressures_pa[key] / 1e6
                if not setting["enabled"]:
                    self.relief_open[key] = False
                elif self.relief_open[key]:
                    if pressure <= setting["close_mpa"]:
                        self.relief_open[key] = False
                elif pressure >= setting["open_mpa"]:
                    self.relief_open[key] = True
                if self.relief_open[key]:
                    events.append(FaultEvent(
                        event_id=f"relief-{key}", kind=FaultKind.HYDROGEN_LEAK,
                        target=target, start_time_s=time_s,
                        leak_diameter_m=setting["orifice_mm"] / 1000.0,
                        rate_s=0.01,
                    ))
        return tuple(events)

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "settings": deepcopy(self.settings),
                "trailer_inventory_kg": self.trailer_mass_kg,
                "trailer_pressure_mpa": self.trailer_state().pressure_pa / 1e6,
                "trailer_transferred_kg": self.trailer_transferred_kg,
                "recharge_transferred_kg": self.recharge_transferred_kg,
                "relief_open": dict(self.relief_open),
                "revision": self.revision,
                "stop_reason": dict(self.stop_reason),
            }
