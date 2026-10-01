"""Integrate model telemetry and existing release consequences with the HAZOP database."""
from __future__ import annotations

import math
from .database import EventStore, load_catalog
from .engine import RuleEngine
from .mapping import GD_SENSOR_ZONES, ModelMapper, coverage
from .flame import FLAME_DETECTORS, FLAME_RESPONSE_DELAY_S, sees_target


class HazopMonitor:
    def __init__(self, catalog=None, run_id=None, store=None, virtual_detectors=False):
        self.catalog = catalog or load_catalog()
        self.engine = RuleEngine(self.catalog)
        self.mapper = ModelMapper(self.catalog["sensors"])
        self.coverage = coverage(self.catalog)
        self.run_id, self.store = run_id, store
        self.latest = None
        self.frames = []
        self.consequence_times = {}
        self.persistence_error = None
        self.virtual_detectors = bool(virtual_detectors)
        if store and run_id: store.start(run_id, self.catalog["metadata"])

    def sample(self, t, *, active_leaks, risk_snapshots, **model):
        detector_multiplier = model.pop("detector_multiplier", None)
        frame = self.mapper.sample(t, active_leaks=active_leaks, risk_snapshots=risk_snapshots, **model)
        # Location-specific detector output is accepted only under an explicit DB sensor ID.
        # Indoor maximum_concentration and virtual:<release> are never copied into a GD.
        for snapshot in risk_snapshots:
            if snapshot.consequence_updated: self.consequence_times[snapshot.release_id] = t
            detectors = snapshot.consequence.get("detector_concentrations", {})
            if isinstance(detectors, dict):
                for tag, fraction in detectors.items():
                    if tag in self.mapper.specs and self.mapper.specs[tag]["종류"] == "G":
                        if not isinstance(fraction,(int,float)) or not math.isfinite(fraction) or not 0 <= fraction <= 1: continue
                        observed_t = self.consequence_times.get(snapshot.release_id, t)
                        old = frame["signals"].get(tag)
                        value = 100.0 * fraction
                        if old is None or value > old["value"]:
                            frame["signals"][tag] = {"value":value,"unit":"vol%_H2","quality":"GOOD", "time_s":observed_t,"origin":"MODEL_DETECTOR_AT_LOCATION"}
        # The digital twin also exposes virtual detector heads at each major zone.
        # These are simulated signals, intentionally labelled so a plant historian can
        # replace the proxy with CFD/HyRAM detector concentrations later.
        zone_detectors = {
            "supply": ("GD-0101", "GD-0201"),
            "unloading": ("GD-0201", "GD-0101"),
            "compressor": ("GD-0601", "GD-2101"),
            "cascade.low": ("GD-0701", "GD-2201"),
            "cascade.medium": ("GD-0801", "GD-2201"),
            "cascade.high": ("GD-0901", "GD-2201"),
            "header": ("GD-1001", "GD-2001"),
            "pcv": ("GD-1301", "GD-2301"),
            "dispenser.hose": ("GD-1301", "GD-2301"),
            "dispenser_2.hose": ("GD-1701", "GD-2301"),
            "vehicle.tank": ("GD-1301", "GD-2301"),
            "vehicle_2.tank": ("GD-1701", "GD-2301"),
            "dispenser": ("GD-1301", "GD-2301"),
            "dispenser_2": ("GD-1701", "GD-2301"),
            "cooler": ("GD-1901", "GD-2302"),
            "vent": ("GD-2001", "GD-1001"),
        }
        if self.virtual_detectors:
            for tag, zone in GD_SENSOR_ZONES.items():
                if tag in self.mapper.specs:
                    frame["signals"].setdefault(tag, {
                        "value": 0.0, "unit": "vol%_H2", "quality": "GOOD",
                        "time_s": t, "origin": "VIRTUAL_DETECTOR_PROXY", "zone": zone,
                    })
            fire_events = tuple(event for event in model.get("fault_events", ())
                                if event.kind.value == "external-fire")
            for tag, _node, zone, targets in FLAME_DETECTORS:
                if tag not in self.mapper.specs:
                    continue
                visible = [event for event in fire_events if sees_target(event.target, targets)]
                detected = any(t - event.start_time_s >= FLAME_RESPONSE_DELAY_S for event in visible)
                frame["signals"][tag] = {
                    "value": float(detected), "unit": "bool", "quality": "GOOD",
                    "time_s": t, "origin": "VIRTUAL_FLAME_DETECTOR_PROXY", "zone": zone,
                    "coverage": "MODELED_TARGET_ONLY",
                }
        for event, leak, _source, _ in active_leaks if self.virtual_detectors else ():
            snap = next((x for x in risk_snapshots if x.release_id == leak.release_id), None)
            mass_flow = float(getattr(snap, "mass_flow_kg_s", 0.0) if snap else 0.0)
            if mass_flow <= 0.0:
                continue
            target = str(event.target).lower()
            key = max((k for k in zone_detectors if target == k or target.startswith(k + ".")), key=len, default="header")
            near_tag, far_tag = zone_detectors[key]
            # Proxy plume: mass release converted to vol% with near/far heads. This
            # is an advisory virtual sensor, not a replacement for consequence CFD.
            dilution = (float(detector_multiplier(target)) if detector_multiplier is not None else 1.0)
            near_value = min(100.0, mass_flow * 10000.0 * dilution)
            for tag, multiplier in ((near_tag, 1.0), (far_tag, 0.45)):
                if tag not in self.mapper.specs or self.mapper.specs[tag]["종류"] != "G":
                    continue
                value = near_value * multiplier
                old = frame["signals"].get(tag)
                if old and old.get("origin") == "MODEL_DETECTOR_AT_LOCATION":
                    continue
                if old is None or value > float(old.get("value", 0.0)):
                    frame["signals"][tag] = {"value": value, "unit": "vol%_H2", "quality": "GOOD",
                                               "time_s": t, "origin": "VIRTUAL_DETECTOR_PROXY", "zone": GD_SENSOR_ZONES[tag]}
        for event in model.get("fault_events", ()):
            if not event.target.startswith(("GD-", "FD-")) or event.target not in frame["signals"]:
                continue
            signal = frame["signals"][event.target]
            if event.kind.value == "sensor-bias":
                signal["value"] += event.magnitude
                signal["origin"] = "SIMULATED_SENSOR_BIAS"
            elif event.kind.value == "sensor-freeze":
                key = (event.event_id, event.target)
                self.mapper.frozen.setdefault(key, signal["value"])
                signal["value"] = self.mapper.frozen[key]
                signal["origin"] = "SIMULATED_SENSOR_FREEZE"
            frame["legacy_plc_sensor_faults"] = [tag for tag in frame["legacy_plc_sensor_faults"] if tag != event.target]
        result = self.engine.evaluate(frame)
        by_release = {x.release_id:x for x in risk_snapshots}
        releases = []
        for event, leak, source, _ in active_leaks:
            snap = by_release.get(leak.release_id)
            consequence = dict(snap.consequence) if snap else {"status":"unavailable"}
            releases.append({"release_id":leak.release_id, "component_id":leak.component_id,
                             "mass_flow_g_s":float(snap.mass_flow_kg_s * 1000.0) if snap else 0.0,
                             "source_pressure_pa":source.pressure_pa,"source_temperature_k":source.temperature_k,
                             "orifice_diameter_m":leak.orifice_diameter_m, "release_evidence":"INJECTED_PHYSICAL_LEAK",
                             "consequence":consequence, "calculated_time_s":self.consequence_times.get(leak.release_id),
                             "cached":not snap.consequence_updated if snap else False,
                             "geometry_status":"SCENARIO_DEFAULTS_NOT_SITE_VALIDATED"})
        cases = {c["case_id"]:c for c in self.catalog["cases"]}
        node_targets = {n["node_id"]:n["누출_target"] for n in self.catalog["nodes"]}
        groups = {}
        for alarm in result["active"]:
            case_id = alarm["case_id"]
            key = alarm["node_id"] + ":" + (case_id or "diagnostic")
            if alarm["sensor_id"].startswith("GD-"):
                key += ":" + alarm["sensor_id"]  # Distinct detector positions are not assumed to share one leak.
            if key not in groups:
                case = cases.get(case_id, {})
                candidates = (case.get("누출원_후보노드") or "").split(";")
                targets = {node_targets.get(n) for n in candidates} - {None, ""}
                linked = [x for x in releases if x["component_id"] in targets]
                status = "NOT_APPLICABLE" if not case_id else "RESULT_LINKED" if any(x["consequence"].get("status")=="calculated" for x in linked) else "BACKEND_UNAVAILABLE" if linked else "NEEDS_RELEASE_INPUTS"
                if status == "RESULT_LINKED" and any(x["consequence"].get("status") != "calculated" or x["consequence"].get("indoor_status") == "enclosure-not-configured" for x in linked):
                    status = "PARTIAL_RESULT"
                groups[key] = {"group_id":key,"node_id":alarm["node_id"],"case_id":case_id,"rule_ids":[],
                               "severity":alarm["severity"],"hyram_status":status,"release_ids":[x["release_id"] for x in linked],
                               "required_inputs":case.get("필수_추가입력"), "scenario_type":"CANDIDATE_NOT_CONFIRMED"}
            groups[key]["rule_ids"].append(alarm["rule_id"])
            if alarm["severity"] == "TRIP": groups[key]["severity"] = "TRIP"
        result.update({"groups":list(groups.values()),"releases":releases,
                       "mapped_sensor_count":sum(k in self.mapper.specs for k in frame["signals"]),
                       "sensor_total":len(self.mapper.specs),"source_sha256":self.catalog["metadata"]["source_sha256"],
                       "legacy_plc_sensor_faults":frame["legacy_plc_sensor_faults"]})
        if self.store and self.run_id:
            try: self.store.append(self.run_id, result["events"])
            except Exception as exc: self.persistence_error = f"{type(exc).__name__}: {exc}"
        result["persistence_error"] = self.persistence_error
        self.latest = {**result, "signals":frame["signals"], "modes":frame["modes"]}
        # Keep transport compact: full rule diagnostics are available from the detail endpoint.
        compact = {k:v for k,v in result.items() if k!="rules"}
        compact["signals"] = frame["signals"]
        compact["modes"] = frame["modes"]
        self.frames.append(compact)
        if len(self.frames) > 12000:
            del self.frames[:-12000]
        return compact

    def summary(self):
        return {"metadata":self.catalog["metadata"],"coverage":self.coverage,
                "events":self.engine.events,"latest":self.latest,"frames":self.frames}
