"""Simulation telemetry mappings; proxy channels are explicitly marked as such."""
from __future__ import annotations

from .flame import FLAME_DETECTORS

MODEL_BINDINGS = {}
for n, bank in (("07", "low"), ("08", "medium"), ("09", "high")):
    MODEL_BINDINGS[f"PT-{n}01"] = ("PROCESS_STATE", f"bank.{bank}.pressure_pa / 1e6")
    MODEL_BINDINGS[f"TT-{n}01"] = ("PROCESS_STATE", f"bank.{bank}.temperature_k - 273.15")
    MODEL_BINDINGS[f"FT-{n}01"] = ("PROCESS_FLOW", f"signed {bank}-bank selector flow into finite common header")
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
MODEL_BINDINGS["FT-1001"] = ("PROCESS_FLOW", "signed total cascade-bank inflow to finite common header")
GD_SENSOR_ZONES = {
    "GD-0101": "tube-trailer supply", "GD-0201": "unloading manifold",
    "GD-0601": "compressor discharge", "GD-0701": "low bank",
    "GD-0801": "medium bank", "GD-0901": "high bank",
    "GD-1001": "cascade header", "GD-1301": "dispenser 1 hose",
    "GD-1701": "dispenser 2 hose", "GD-1901": "cooling package",
    "GD-2001": "vent header", "GD-2101": "compressor cabinet",
    "GD-2201": "storage boundary", "GD-2301": "fueling canopy",
    "GD-2302": "cooling enclosure",
}
for tag, zone in GD_SENSOR_ZONES.items():
    MODEL_BINDINGS[tag] = ("VIRTUAL_DETECTOR_PROXY", f"location-specific leak proxy at {zone}; 0 when no active release")
for tag, _node, zone, targets in FLAME_DETECTORS:
    MODEL_BINDINGS[tag] = ("VIRTUAL_FLAME_DETECTOR_PROXY",
                           f"simulated optical flame line-of-sight at {zone}; modeled targets: {', '.join(targets)}")
for node in ("01", "02", "03", "04", "05", "06"):
    MODEL_BINDINGS[f"FT-{node}01"] = ("DERIVED_COMPRESSOR", "compressor mass flow to selected recharge bank; shared flow, no line loss model")
for tag in ("PT-0201", "PT-0302"):
    MODEL_BINDINGS[tag] = ("BOUNDARY_SETTING", "compressor suction pressure; unloading line drop not modeled")
MODEL_BINDINGS["TT-0201"] = ("BOUNDARY_SETTING", "compressor suction temperature; unloading hose heat transfer not modeled")
for stage, node in ((1, "04"), (2, "05")):
    MODEL_BINDINGS[f"PT-{node}01"] = ("COMPRESSOR_STAGE_MODEL", f"compressor stage {stage} discharge pressure")
    MODEL_BINDINGS[f"TT-{node}01"] = ("COMPRESSOR_STAGE_MODEL", f"compressor stage {stage} discharge temperature")
    MODEL_BINDINGS[f"TT-{node}02"] = ("BOUNDARY_SETTING", f"compressor stage {stage} intercooler outlet temperature setpoint")
MODEL_BINDINGS.update({
    "PT-0601": ("COMPRESSOR_STAGE_MODEL", "compressor final discharge pressure"),
    "TT-0601": ("COMPRESSOR_STAGE_MODEL", "compressor final discharge temperature"),
    "TT-0602": ("PROCESS_STATE", "selected recharge bank gas temperature; no separate discharge line inventory"),
    "PT-1001": ("PROCESS_STATE", "finite common-header pressure"),
    "TT-1001": ("PROCESS_STATE", "finite common-header gas temperature"),
    "PT-1201": ("DERIVED_SHARED", "dispenser 1 PCV outlet pressure less precooler hydrogen pressure drop"),
    "PT-1601": ("DERIVED_SHARED", "dispenser 2 PCV outlet pressure less precooler hydrogen pressure drop"),
    "FT-1901": ("DERIVED_THERMAL_PROXY", "coolant equivalent L/min from total heat rate / (water cp * assumed 5 K rise)"),
    "TT-1901": ("PROCESS_STATE", "dispenser 1 coolant thermal inventory temperature"),
    "TT-1902": ("PROCESS_STATE", "dispenser 2 coolant thermal inventory temperature"),
    "PT-0001": ("ASSUMED_BOUNDARY", "ambient atmospheric pressure, 0.101325 MPa absolute"),
    "PT-2001": ("VENT_PROXY", "vent release source pressure when injected; ambient otherwise"),
    "TT-2001": ("VENT_PROXY", "vent release source temperature when injected; ambient otherwise"),
    "FT-2001": ("VENT_PROXY", "vent release mass flow when injected; zero otherwise; no PSV model"),
})
HELPERS = {"MASS_HOSE_1", "MASS_HOSE_2", "MASS_HEADER"}
# The bank-header selector paths and two dispenser-nozzle restrictions have an
# explicit reverse-flow path enabled only by a simulated check-valve failure.
# Other flow channels remain one-way or derived shared signals.
REVERSE_FLOW_CAPABLE_SIGNALS = {
    "FT-0701", "FT-0801", "FT-0901", "FT-1001", "FT-1301", "FT-1701",
}
MODE_KEYS = {
    "station.monitoring", "station.filling_count", "station.switch_elapsed_s",
    "station.esd", "station.esd_elapsed_s",
    "compressor.running", "compressor.elapsed_s", "compressor.stop_elapsed_s",
    "unloading.active", "unloading.elapsed_s",
    "unloading.disconnect_requested", "unloading.depressurize_elapsed_s",
    "cooling.enabled", "cooling.elapsed_s",
    "vent.commanded", "vent.close_elapsed_s", "relief.active",
}
for d in (1, 2):
    MODE_KEYS |= {f"d{d}.{k}" for k in (
        "phase", "phase_elapsed_s", "switch_elapsed_s", "connected",
        "pcv_closed", "nozzle_closed", "bleed_active", "stable_s",
    )}
for n in ("07", "08", "09"):
    MODE_KEYS |= {f"bank.{n}.{k}" for k in (
        "dispatch", "switch_elapsed_s", "inlet_closed", "outlet_closed",
        "relief_active", "stable_s",
    )}


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
        issues = []
        if (r["sensor_id"].startswith("FT-") and r["연산자"] == "<=" and
                r["임계값"] < 0 and r["sensor_id"] not in REVERSE_FLOW_CAPABLE_SIGNALS):
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
               dispatch_openings, recharge_index, safety, fault_events=(), active_leaks=(), risk_snapshots=(),
               compressor_flow_multiplier=1.0, process_snapshot=None,
               virtual_safety_snapshot=None):
        signals, modes = {}, {"station.monitoring": True, "station.esd": safety.esd_latched,
                              "station.scenario_active": bool(fault_events or active_leaks)}
        compressor_temperature_tags = {"TT-0401", "TT-0501", "TT-0601"}
        compressor_thermal_targets = {
            "compressor", "compressor.stage1", "compressor.stage2",
            "compressor.stage3", "N04", "N05", "N06",
        }
        modes["compressor.thermal_event"] = any(
            (
                event.kind.value in ("external-fire", "temperature-disturbance")
                and (
                    event.target in compressor_thermal_targets
                    or event.target.startswith("compressor.")
                )
            )
            or (
                event.kind.value in ("sensor-bias", "sensor-freeze")
                and event.target in compressor_temperature_tags
            )
            for event in fault_events
        )
        active_relief_targets = {
            event.target for event, _leak, _source, _location in active_leaks
            if event.event_id.startswith("relief-")
        }
        vent_commanded = any(
            event.event_id.startswith("vent-")
            for event, _leak, _source, _location in active_leaks
        )
        relief_active = bool(active_relief_targets)
        vent_path_active = vent_commanded or relief_active
        vent_path_elapsed_s = self.elapsed("vent-path-active", vent_path_active, t)
        modes.update({
            "vent.commanded": vent_commanded,
            "relief.active": relief_active,
            "vent.close_elapsed_s": 0.0 if vent_path_active else vent_path_elapsed_s,
        })
        def put(tag, value, unit=None, origin=None):
            signals[tag] = {"value": float(value), "unit": unit or self.specs[tag]["단위"], "quality": "GOOD",
                            "time_s": t, "origin": origin or MODEL_BINDINGS[tag][0]}
        modes["station.esd_elapsed_s"] = self.elapsed("esd", safety.esd_latched, t) if safety.esd_latched else 0.0
        if not safety.esd_latched: self.elapsed("esd", False, t)
        modes["station.filling_count"] = sum(c.phase.value == "filling" for c in commands)
        modes["station.switch_elapsed_s"] = self.elapsed("dispatch", dispatch_indices, t)
        bank_gases = [bank.gas_state(bank_state) for bank, bank_state in zip(station.banks, state.banks)]
        header_reverse_enabled = any(
            getattr(getattr(event, "kind", None), "value", None) == "check-valve-failure"
            and event.target in {"header", "cascade.header", "check-valve"}
            for event in fault_events
        )
        header_flows = station.header_bank_mass_flows(
            state,
            tuple(dispatch_indices),
            tuple(dispatch_openings),
            allow_reverse_flow=header_reverse_enabled,
        )
        header_gas = station.header_gas_state(state)
        for index, bank in enumerate(station.banks):
            z = str(7+index).zfill(2)
            gas = bank_gases[index]
            put(f"PT-{z}01", gas.pressure_pa/1e6); put(f"TT-{z}01", gas.temperature_k-273.15)
            if header_gas is not None:
                bank_flow = header_flows[index]
            else:
                bank_flow = sum(
                    inst["pcv_mass_flow"]
                    for inst, selected in zip(instantaneous, dispatch_indices)
                    if selected == index
                )
            put(f"FT-{z}01", bank_flow * 1000)
            selected = index in dispatch_indices
            actual_out_open = any(i == index and op > 0 for i, op in zip(dispatch_indices, dispatch_openings))
            modes.update({f"bank.{z}.dispatch": selected,
                          f"bank.{z}.switch_elapsed_s": self.elapsed(f"bank{z}", selected, t),
                          f"bank.{z}.inlet_closed": recharge_index != index,
                          f"bank.{z}.outlet_closed": not actual_out_open,
                          f"bank.{z}.relief_active": f"cascade.{bank.parameters.name}" in active_relief_targets,
                          f"bank.{z}.stable_s": self.elapsed(f"isolation{z}", (recharge_index==index, actual_out_open), t)})
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
            put(f"PT-{p+1}01", max(0.0, (inst["pcv_outlet_pressure"] - partial.precooler.hydrogen_pressure_drop_pa)/1e6))
            put(f"MASS_HOSE_{d}", partial_state.hose_hydrogen_mass_kg, "kg", "PROCESS_INVENTORY")
            commanded_isolation = bool(
                safety.esd_latched
                or command.phase.value in ("idle", "complete", "aborted")
                or command.valve_opening <= 0.0
            )
            isolation_stable_s = self.elapsed(
                f"d{d}-commanded-isolation", commanded_isolation, t
            )
            modes.update({f"d{d}.phase": "ESD" if safety.esd_latched else command.phase.value.upper(),
                          f"d{d}.phase_elapsed_s": self.elapsed(f"phase{d}", command.phase, t),
                          f"d{d}.switch_elapsed_s": self.elapsed(f"dispatch{d}", selected, t),
                          f"d{d}.connected": True,  # Fixed connected-vehicle model topology, not connector telemetry.
                          f"d{d}.pcv_closed": commanded_isolation,
                          f"d{d}.nozzle_closed": commanded_isolation,
                          f"d{d}.bleed_active": False,
                          f"d{d}.stable_s": isolation_stable_s if commanded_isolation else 0.0})
        supply = station.compressor_suction(t)
        for n in ("01", "03"):
            put(f"PT-{n}01", supply.pressure_pa/1e6); put(f"TT-{n}01", supply.temperature_k-273.15)
        line_pressures = (virtual_safety_snapshot or {}).get("line_pressure_mpa") or {}
        unloading_pressure_mpa = line_pressures.get("trailer.station")
        if not isinstance(unloading_pressure_mpa, (int, float)):
            unloading_pressure_mpa = supply.pressure_pa / 1e6
        put("PT-0201", unloading_pressure_mpa); put("PT-0302", supply.pressure_pa/1e6)
        put("TT-0201", supply.temperature_k-273.15)
        virtual_valves = (virtual_safety_snapshot or {}).get("valves") or {}
        required_isolation = tuple(
            virtual_valves.get(name) or {}
            for name in ("trailer.source", "trailer.station")
        )
        unloading_isolated = bool(virtual_valves) and all(
            valve.get("status") == "confirmed"
            and not valve.get("actual_open", True)
            and not valve.get("feedback_open", True)
            and float(valve.get("flow_fraction", 1.0)) <= 0.0
            for valve in required_isolation
        )
        vehicles = (virtual_safety_snapshot or {}).get("vehicles") or {}
        disconnect_requested = vehicles.get("trailer") == 0
        process_settings = (process_snapshot or {}).get("settings") or {}
        transfer_stopped = not (
            process_settings.get("trailer_supply", False)
            or process_settings.get("pressure_recharge", False)
        )
        depressurizing = bool(disconnect_requested and unloading_isolated and transfer_stopped)
        depressurize_elapsed_s = self.elapsed(
            "unloading-depressurizing", depressurizing, t
        )
        modes.update({
            "unloading.disconnect_requested": disconnect_requested,
            "unloading.depressurize_elapsed_s": (
                depressurize_elapsed_s if depressurizing else 0.0
            ),
        })
        discharge = (bank_gases[recharge_index].pressure_pa + station.compressor.parameters.discharge_pressure_margin_pa
                     if recharge_index is not None else supply.pressure_pa)
        compressor = station.compressor.evaluate(supply, discharge, enabled=recharge_index is not None,
                                                 include_stage_outlets=True)
        compressor_flow_kg_s = max(
            0.0, compressor.mass_flow_kg_s * compressor_flow_multiplier
        )
        compressor_running = compressor_flow_kg_s > 1.0e-9
        compressor_elapsed_s = self.elapsed("compressor-running", compressor_running, t)
        modes.update({
            "compressor.running": compressor_running,
            "compressor.elapsed_s": compressor_elapsed_s if compressor_running else 0.0,
            "compressor.stop_elapsed_s": 0.0 if compressor_running else compressor_elapsed_s,
            "unloading.active": compressor_running,
            "unloading.elapsed_s": compressor_elapsed_s if compressor_running else 0.0,
        })
        for n in ("01", "02", "03", "04", "05", "06"):
            put(f"FT-{n}01", compressor.mass_flow_kg_s*compressor_flow_multiplier*1000)
        for stage, node in ((0,"04"), (1,"05")):
            pressure, temperature = (compressor.stage_outlets[stage] if len(compressor.stage_outlets)>stage
                                     else (supply.pressure_pa, supply.temperature_k))
            put(f"PT-{node}01", pressure/1e6)
            put(f"TT-{node}01", temperature-273.15)
            put(f"TT-{node}02", station.compressor.parameters.intercooler_outlet_temperature_k-273.15)
        put("PT-0601", discharge/1e6)
        put("TT-0601", compressor.outlet_temperature_k-273.15)
        put("TT-0602", bank_gases[recharge_index].temperature_k-273.15 if recharge_index is not None else supply.temperature_k-273.15)
        if header_gas is not None and state.common_header is not None:
            put("PT-1001", header_gas.pressure_pa / 1e6)
            put("TT-1001", header_gas.temperature_k - 273.15)
            put("FT-1001", sum(header_flows) * 1000)
            put(
                "MASS_HEADER",
                state.common_header.hydrogen_mass_kg,
                "kg",
                "PROCESS_INVENTORY",
            )
        else:
            selected = [inst for inst, index in zip(instantaneous, dispatch_indices) if index is not None]
            header = selected or [instantaneous[0]]
            put("PT-1001", max(inst["supply_pressure"] for inst in header)/1e6)
            total_flow = sum(max(0.0,inst["pcv_mass_flow"]) for inst in header)
            put("TT-1001", (sum(inst["supply_temperature"]*max(0.0,inst["pcv_mass_flow"]) for inst in header)/total_flow
                             if total_flow else header[0]["supply_temperature"])-273.15)
            put("FT-1001", sum(inst["pcv_mass_flow"] for inst in instantaneous)*1000)
        coolant_states = (state.partial_station, state.secondary_partial_station)
        for tag, coolant in zip(("TT-1901","TT-1902"), coolant_states):
            put(tag, coolant.coolant_temperature_k-273.15)
        heat_w = sum(abs(inst["precooler_heat_rate"]) for inst in instantaneous)
        put("FT-1901", heat_w/(4180.0*5.0)*60.0, origin="DERIVED_THERMAL_PROXY")
        cooling_enabled = bool(heat_w > 1.0e-6)
        cooling_elapsed_s = self.elapsed("cooling-enabled", cooling_enabled, t)
        modes.update({
            "cooling.enabled": cooling_enabled,
            "cooling.elapsed_s": cooling_elapsed_s if cooling_enabled else 0.0,
        })
        put("PT-0001", 0.101325)
        vent = next(((source, snap) for event, leak, source, _ in active_leaks
                     for snap in risk_snapshots if event.target.startswith("vent") and snap.release_id==leak.release_id), None)
        put("PT-2001", vent[0].pressure_pa/1e6 if vent else 0.101325)
        put("TT-2001", vent[0].temperature_k-273.15 if vent else station.ambient_temperature_k-273.15)
        put("FT-2001", vent[1].mass_flow_kg_s*1000 if vent else 0.0)
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
