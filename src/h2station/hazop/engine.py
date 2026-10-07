"""Stateful advisory rules with quality gates, persistence, hysteresis and manual latches."""
from __future__ import annotations

from collections import Counter
from math import isfinite
from .expressions import Evaluator, Unknown, compare, evaluate_gate, dependencies
from .mapping import coverage


# The H70 PCV intentionally throttles a high-pressure bank into a low-pressure
# vehicle. A large differential alone is normal while hydrogen is flowing.
PCV_DROP_FLOW_TAGS = {"HZ-081": "FT-1101", "HZ-109": "FT-1501"}
# These rules diagnose a requested fill only after an injected disturbance is
# present. The virtual PCV/hose line-pack model has normal start-up and bank-
# switching transients that otherwise look like momentary no-flow, high dP,
# warm outlet, or pressure-ramp deviations.
SCENARIO_QUALIFIED_FILL_RULES = {
    "HZ-077", "HZ-081", "HZ-082", "HZ-092", "HZ-100",
    "HZ-105", "HZ-109", "HZ-110", "HZ-120", "HZ-128",
}
# The workbook marks these pre-intercooler stage-discharge limits as
# PROPOSED and site_activation=false. Normal multistage compression produces
# hot gas at these points, so the unapproved 45/60 degC limits must not create
# guaranteed alarms during ordinary operation. Keep the source rules intact
# and qualify them with a relevant thermal or sensor-fault exercise until an
# OEM/site limit is approved.
SCENARIO_QUALIFIED_COMPRESSOR_TEMPERATURE_RULES = {
    "HZ-019", "HZ-020", "HZ-027", "HZ-028", "HZ-035", "HZ-036",
}


class RuleEngine:
    def __init__(self, catalog):
        self.catalog = catalog
        self.specs = {s["sensor_id"]: s for s in catalog["sensors"]}
        self.gates = {g["gate_id"]: g["기계식_상태조건"] for g in catalog["gates"]}
        self.coverage = {r["rule_id"]: r for r in coverage(catalog)["rules"]}
        self.history = []
        self.states = {}
        self.events = []
        self.next_sequence = 0
        self.last_time = None
        self.max_window = max((r["window_s"] for r in catalog["rules"]), default=0) + 3

    def evaluate(self, frame, reset_requests=frozenset()):
        t = frame["time_s"]
        if self.last_time is not None and t <= self.last_time: raise ValueError("HAZOP timestamps must strictly increase")
        interval = None if self.last_time is None else t - self.last_time
        self.last_time = t
        self.history.append(frame)
        while len(self.history)>2 and self.history[1]["time_s"] < t-self.max_window: self.history.pop(0)
        evaluator = Evaluator(self.history, self.specs)
        new_events, output = [], []
        for r in self.catalog["rules"]:
            rid = r["rule_id"]
            memory = self.states.setdefault(rid, {"since":None, "reset_since":None, "active":False, "status":"INITIAL"})
            previous = memory["status"]
            value, reason, quality = None, "", "GOOD"
            gate = evaluate_gate(self.gates[r["gate_id"]], frame["modes"])
            if (gate is True and rid in SCENARIO_QUALIFIED_FILL_RULES
                    and frame["modes"].get("station.scenario_active") is False):
                gate = False
            if (gate is True and rid in SCENARIO_QUALIFIED_COMPRESSOR_TEMPERATURE_RULES
                    and frame["modes"].get("compressor.thermal_event") is False):
                gate = False
            if gate is True and rid in PCV_DROP_FLOW_TAGS:
                flow_tag = PCV_DROP_FLOW_TAGS[rid]
                flow = frame["signals"].get(flow_tag)
                try:
                    flow_value = float(flow["value"]) if flow is not None else float("nan")
                    flow_age = t - float(flow["time_s"]) if flow is not None else float("inf")
                except (KeyError, TypeError, ValueError):
                    flow_value = float("nan")
                    flow_age = float("inf")
                if (flow is None or flow.get("quality") != "GOOD" or not isfinite(flow_value)
                        or not 0.0 <= flow_age <= self.specs[flow_tag]["최대데이터나이_s"]):
                    gate = None
                    reason = "MISSING_PCV_FLOW"
                elif flow_value > 1.0:
                    gate = False
            if gate is False:
                state = "INACTIVE"
                memory["since"] = memory["reset_since"] = None
                if not r["래치"]: memory["active"] = False
            elif gate is None:
                state, reason, quality = "UNKNOWN", reason or "MISSING_MODE", "UNKNOWN"
                memory["since"] = memory["reset_since"] = None
            else:
                try:
                    max_gap = min((self.specs[tag]["최대데이터나이_s"] for tag in dependencies(r["신호식"]) if tag in self.specs), default=1.0)
                    if interval is not None and interval > max_gap+1e-9 and not r["신호식"].startswith("AGE("):
                        raise Unknown("SAMPLING_GAP")
                    limits = self.coverage[rid]["model_limits"]
                    if limits: raise Unknown("MODEL_LIMIT:" + "; ".join(limits))
                    value = evaluator.evaluate(r["신호식"], frame)
                    if compare(value, r["연산자"], r["임계값"]):
                        memory["reset_since"] = None
                        if memory["since"] is None: memory["since"] = t
                        if t-memory["since"]+1e-9 >= r["지속_s"]:
                            memory["active"] = True
                            state = "TRIGGER"
                        else: state = "PENDING"
                    else:
                        memory["since"] = None
                        clear = compare(value, r["복귀연산자"], r["복귀값"])
                        if clear:
                            if memory["reset_since"] is None: memory["reset_since"] = t
                            can_reset = t-memory["reset_since"]+1e-9 >= r["복귀지속_s"]
                            if can_reset and (not r["래치"] or rid in reset_requests): memory["active"] = False
                        else: memory["reset_since"] = None
                        state = "NORMAL"
                except (Unknown, ValueError, OverflowError) as exc:
                    state, reason, quality = "UNKNOWN", str(exc), "UNKNOWN"
                    memory["since"] = memory["reset_since"] = None
            condition_status = state
            if memory["active"] and state != "TRIGGER": state = "LATCHED" if r["래치"] else "ALARM_HOLD"
            memory["status"] = state
            item = {"rule_id":rid, "node_id":r["node_id"], "sensor_id":r["sensor_id"], "name":r["시나리오명"],
                    "state":state, "condition_status":condition_status, "quality":quality, "reason":reason,
                    "value":value, "operator":r["연산자"], "threshold":r["임계값"], "unit":r["단위"],
                    "persistence_s":r["지속_s"], "severity":r["등급"], "case_id":r["HyRAM_case_id"],
                    "active":memory["active"], "gate":gate, "rule_version":r["rule_version"],
                    "basis":r["기준구분"], "time_s":t}
            output.append(item)
            # Initial missing signals are coverage, not 200 simultaneous alarm events.
            if state != previous and (memory["active"] or previous in ("TRIGGER","LATCHED","ALARM_HOLD")):
                event = {**item, "sequence":self.next_sequence, "previous_state":previous,
                         "source_sha256":self.catalog["metadata"]["source_sha256"],
                         "signal_snapshot":{tag:frame["signals"].get(tag) for tag in dependencies(r["신호식"])},
                         "mode_snapshot":dict(frame["modes"]), "classification":"ACCIDENT_CANDIDATE" if memory["active"] else "CLEARED"}
                self.events.append(event); new_events.append(event)
                self.next_sequence += 1
        if len(self.events) > 5000:
            del self.events[:-5000]
        return {"time_s":t, "counts":dict(Counter(x["state"] for x in output)),
                "active":[x for x in output if x["active"]], "events":new_events, "rules":output,
                "mode":"SIMULATION_ADVISORY", "physical_plc_actions":False}
