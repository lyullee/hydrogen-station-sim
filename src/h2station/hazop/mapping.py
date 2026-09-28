"""Explicit mappings to existing model states, with no fabricated GD/utility readings."""
from __future__ import annotations

MODEL_BINDINGS = {}
for n, bank in (("07", "low"), ("08", "medium"), ("09", "high")):
    MODEL_BINDINGS[f"PT-{n}01"] = ("PROCESS_STATE", f"bank.{bank}.pressure_pa / 1e6")
    MODEL_BINDINGS[f"TT-{n}01"] = ("PROCESS_STATE", f"bank.{bank}.temperature_k - 273.15")
    MODEL_BINDINGS[f"FT-{n}01"] = ("DERIVED_SHARED", f"sum of dispatched PCV flows from {bank}; not an independent meter")
for d, p, h, v in ((1, "11", "13", "14"), (2, "15", "17", "18")):
    hx = str(int(p)+1)
    for tag, binding in {
        f"PT-{p}01": "supply_pressure/1e6", f"TT-{p}01": "supply_temperature-273.15",
        f"PT-{p}02": "pcv_outlet_pressure/1e6", f"FT-{p}01": "pcv_mass_flow*1000",
        f"TT-{hx}01": "precooler_outlet_temperature-273.15",
        f"PT-{h}01": "hose.pressure_pa/1e6", f"TT-{h}01": "hose.temperature_k-273.15",
        f"FT-{h}01": "nozzle_mass_flow*1000", f"PT-{v}01": "vehicle.pressure_pa/1e6",
        f"TT-{v}01": "vehicle.temperature_k-273.15", f"TT-{v}02": "vehicle.shell_temperature_k-273.15",
    }.items(): MODEL_BINDINGS[tag] = ("PROCESS_STATE", f"d{d}.{binding}")
    MODEL_BINDINGS[f"FT-{hx}01"] = ("DERIVED_SHARED", f"d{d}.pcv_mass_flow*1000; HX has no separate inventory")
for n in ("01", "03"):
    MODEL_BINDINGS[f"PT-{n}01"] = ("BOUNDARY_SETTING", "compressor_suction.pressure_pa/1e6; fixed supply, not trailer depletion")
    MODEL_BINDINGS[f"TT-{n}01"] = ("BOUNDARY_SETTING", "compressor_suction.temperature_k-273.15; not measured trailer gas")
MODEL_BINDINGS["FT-1001"] = ("DERIVED_SHARED", "FT-1101 + FT-1501; cannot independently detect header mass loss")
HELPERS = {"MASS_HOSE_1", "MASS_HOSE_2"}
MODE_KEYS = {"station.monitoring", "station.filling_count", "station.switch_elapsed_s", "station.esd", "station.esd_elapsed_s"}
for d in (1, 2):
    MODE_KEYS |= {f"d{d}.{k}" for k in ("phase", "phase_elapsed_s", "switch_elapsed_s", "connected", "pcv_closed")}
for n in ("07", "08", "09"):
    MODE_KEYS |= {f"bank.{n}.{k}" for k in ("dispatch", "switch_elapsed_s", "inlet_closed", "outlet_closed", "stable_s")}


def mapping_catalog(sensors):
    records = []
    for s in sensors:
        kind, binding = MODEL_BINDINGS.get(s["sensor_id"], ("UNAVAILABLE", "No independent model state or telemetry input"))
        records.append({"sensor_id": s["sensor_id"], "node_id": s["node_id"], "unit": s["단위"],
                        "mapping_status": kind, "binding": binding, "origin": "SIMULATION", "physical_sensor_connected": False})
    return records


def coverage(catalog):
    from .expressions import dependencies, gate_dependencies
    rows = []
    gates = {g["gate_id"]: g for g in catalog["gates"]}
    for r in catalog["rules"]:
        missing = sorted(dependencies(r["신호식"]) - set(MODEL_BINDINGS) - HELPERS)
        modes = sorted(gate_dependencies(gates[r["gate_id"]]["기계식_상태조건"]) - MODE_KEYS)
        issues = (["isothermal EOS conversion not implemented"] if "P_ISOTHERM" in r["신호식"] else [])
        if r["sensor_id"].startswith("FT-") and r["연산자"] == "<=" and r["임계값"] < 0:
            issues.append("one-way restriction model cannot generate reverse flow")
        ready = not missing and not modes and not issues
        rows.append({"rule_id": r["rule_id"], "node_id": r["node_id"], "simulation_ready": ready,
                     "missing_signals": missing, "missing_modes": modes, "model_limits": issues})
    return {"sensor_total": len(catalog["sensors"]), "mapped_sensors": len(MODEL_BINDINGS),
            "rule_total": len(rows), "simulation_ready_rules": sum(r["simulation_ready"] for r in rows),
            "physical_sensor_connections": 0, "rules": rows, "sensors": mapping_catalog(catalog["sensors"])}


class ModelMapper:
    def __init__(self, sensors):
        self.specs = {s["sensor_id"]: s for s in sensors}
        self.transitions = {}
        self.frozen = {}

    def elapsed(self, key, value, t):
        if key not in self.transitions or self.transitions[key][0] != value:
            self.transitions[key] = (value, t)
        return t - self.transitions[key][1]

    def sample(self, t, *, station, state, commands, instantaneous, dispatch_indices,
               dispatch_openings, recharge_index, safety, fault_events=()):
        signals, modes = {}, {"station.monitoring": True, "station.esd": safety.esd_latched}
        def put(tag, value, unit=None, origin=None):
            signals[tag] = {"value": float(value), "unit": unit or self.specs[tag]["단위"], "quality": "GOOD",
                            "time_s": t, "origin": origin or MODEL_BINDINGS[tag][0]}
        modes["station.esd_elapsed_s"] = self.elapsed("esd", safety.esd_latched, t) if safety.esd_latched else 0.0
        if not safety.esd_latched: self.elapsed("esd", False, t)
        modes["station.filling_count"] = sum(c.phase.value == "filling" for c in commands)
        modes["station.switch_elapsed_s"] = self.elapsed("dispatch", dispatch_indices, t)
        for index, bank in enumerate(station.banks):
            z = str(7+index).zfill(2)
            gas = bank.gas_state(state.banks[index])
            put(f"PT-{z}01", gas.pressure_pa/1e6); put(f"TT-{z}01", gas.temperature_k-273.15)
            flows = [inst["pcv_mass_flow"] for inst, selected in zip(instantaneous, dispatch_indices) if selected == index]
            put(f"FT-{z}01", sum(flows)*1000)
            selected = index in dispatch_indices
            actual_out_open = any(i == index and op > 0 for i, op in zip(dispatch_indices, dispatch_openings))
            modes.update({f"bank.{z}.dispatch": selected,
                          f"bank.{z}.switch_elapsed_s": self.elapsed(f"bank{z}", selected, t),
                          f"bank.{z}.inlet_closed": recharge_index != index,
                          f"bank.{z}.outlet_closed": not actual_out_open,
                          f"bank.{z}.stable_s": self.elapsed(f"isolation{z}", (recharge_index==index, actual_out_open), t)})
            # relief.active is intentionally unknown: no vessel PSV in the full station loop.
        for d, partial, partial_state, command, inst, selected, opening in zip(
            (1,2), (station.partial_station, station.secondary_partial_station),
            (state.partial_station, state.secondary_partial_station), commands, instantaneous, dispatch_indices, dispatch_openings):
            p = 11 if d == 1 else 15; h, v = p+2, p+3
            hose, vehicle = partial.hose_gas_state(partial_state), partial.vehicle_tank.gas_state(partial_state.vehicle)
            put(f"PT-{p}01", inst["supply_pressure"]/1e6); put(f"TT-{p}01", inst["supply_temperature"]-273.15)
            put(f"PT-{p}02", inst["pcv_outlet_pressure"]/1e6); put(f"FT-{p}01", inst["pcv_mass_flow"]*1000)
            put(f"TT-{p+1}01", inst["precooler_outlet_temperature"]-273.15); put(f"FT-{p+1}01", inst["pcv_mass_flow"]*1000)
            put(f"PT-{h}01", hose.pressure_pa/1e6); put(f"TT-{h}01", hose.temperature_k-273.15)
            put(f"FT-{h}01", inst["nozzle_mass_flow"]*1000)
            put(f"PT-{v}01", vehicle.pressure_pa/1e6); put(f"TT-{v}01", vehicle.temperature_k-273.15)
            put(f"TT-{v}02", partial_state.vehicle.shell_temperature_k-273.15)
            put(f"MASS_HOSE_{d}", partial_state.hose_hydrogen_mass_kg, "kg", "PROCESS_INVENTORY")
            modes.update({f"d{d}.phase": command.phase.value.upper(),
                          f"d{d}.phase_elapsed_s": self.elapsed(f"phase{d}", command.phase, t),
                          f"d{d}.switch_elapsed_s": self.elapsed(f"dispatch{d}", selected, t),
                          f"d{d}.connected": True,  # Fixed connected-vehicle model topology, not connector telemetry.
                          f"d{d}.pcv_closed": bool(command.valve_opening * opening == 0.0)})
        supply = station.compressor_suction(t)
        for n in ("01", "03"):
            put(f"PT-{n}01", supply.pressure_pa/1e6); put(f"TT-{n}01", supply.temperature_k-273.15)
        put("FT-1001", sum(inst["pcv_mass_flow"] for inst in instantaneous)*1000)
        # Only explicit DB-tag faults affect these channels. Legacy aggregate PLC faults cannot
        # be attributed to one physical sensor, so remain separate and are reported in the frame.
        for event in fault_events:
            if event.target not in signals: continue
            if event.kind.value == "sensor-bias":
                signals[event.target]["value"] += event.magnitude
                signals[event.target]["origin"] = "SIMULATED_SENSOR_BIAS"
            elif event.kind.value == "sensor-freeze":
                key = (event.event_id, event.target)
                self.frozen.setdefault(key, signals[event.target]["value"])
                signals[event.target]["value"] = self.frozen[key]
                signals[event.target]["origin"] = "SIMULATED_SENSOR_FREEZE"
        return {"time_s": t, "signals": signals, "modes": modes,
                "time_basis": "SIMULATION_SECONDS", "legacy_plc_sensor_faults": [e.target for e in fault_events if e.kind.value in ("sensor-bias","sensor-freeze") and e.target not in signals]}
