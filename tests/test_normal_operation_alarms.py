"""Expected filling and recharge must not masquerade as accident alarms."""

import pytest

from h2station.api import ProcessSettings
from h2station.hazop.database import load_catalog
from h2station.hazop.engine import RuleEngine
from h2station.hazop.runtime import HazopMonitor
from h2station.operations import ProcessRuntime
from h2station.risk.runtime_backend import UnavailableHyRAMBackend
from h2station.scenario import ReferenceScenario, build_reference_scenario


def test_default_recharge_targets_remain_below_sensor_alarm_thresholds():
    settings = ProcessSettings()
    rules = {rule["rule_id"]: rule for rule in load_catalog()["rules"]}
    for bank, rule_id in (("low", "HZ-043"), ("medium", "HZ-052"), ("high", "HZ-061")):
        assert getattr(settings, f"recharge_target_{bank}_mpa") < rules[rule_id]["임계값"]


@pytest.mark.parametrize("rule_id,flow_tag", [("HZ-081", "FT-1101"), ("HZ-109", "FT-1501")])
def test_pcv_pressure_drop_alarm_requires_low_flow(rule_id, flow_tag):
    dispenser = 1 if flow_tag == "FT-1101" else 2
    inlet = f"PT-{11 if dispenser == 1 else 15}01"
    outlet = f"PT-{11 if dispenser == 1 else 15}02"

    def decision(flow_g_s):
        engine = RuleEngine(load_catalog())
        for time_s in (0.0, 1.0, 2.0, 3.0):
            signals = {
                inlet: {"value": 90.0, "unit": "MPa_abs", "quality": "GOOD", "time_s": time_s},
                outlet: {"value": 50.0, "unit": "MPa_abs", "quality": "GOOD", "time_s": time_s},
                flow_tag: {"value": flow_g_s, "unit": "g/s", "quality": "GOOD", "time_s": time_s},
            }
            result = engine.evaluate({"time_s": time_s, "signals": signals, "modes": {
                f"d{dispenser}.phase": "FILLING",
                f"d{dispenser}.phase_elapsed_s": 5.0,
                f"d{dispenser}.switch_elapsed_s": 5.0,
            }})
        return next(rule for rule in result["rules"] if rule["rule_id"] == rule_id)

    assert decision(5.0)["active"] is False
    assert decision(0.0)["active"] is True


@pytest.mark.parametrize("operations", [
    ("vehicle_1",),
    ("vehicle_2",),
    ("trailer_supply", "pressure_recharge", "vehicle_1", "vehicle_2"),
])
def test_normal_process_requests_have_no_hazop_alarm(operations):
    settings = ProcessSettings(**{operation: True for operation in operations}).model_dump()
    built = build_reference_scenario(
        ReferenceScenario(duration_s=12.0, control_period_s=0.5), UnavailableHyRAMBackend()
    )
    process = ProcessRuntime(settings)
    built.simulator.process_runtime = process
    built.station.compressor_suction = lambda _time: process.trailer_state()
    built.simulator.hazop_monitor = HazopMonitor(virtual_detectors=True)
    active = []
    built.simulator.simulate(
        built.initial_state, 12.0, 0.5,
        sample_callback=lambda sample: active.extend(sample.hazop["active"]),
    )
    assert active == []


def test_proposed_compressor_temperature_limits_require_relevant_exercise():
    def decision(thermal_event):
        engine = RuleEngine(load_catalog())
        for time_s in (0.0, 1.0, 2.0, 3.0):
            result = engine.evaluate({
                "time_s": time_s,
                "signals": {
                    "TT-0401": {
                        "value": 95.0, "unit": "degC", "quality": "GOOD",
                        "time_s": time_s,
                    },
                },
                "modes": {
                    "compressor.running": True,
                    "compressor.elapsed_s": 10.0,
                    "compressor.thermal_event": thermal_event,
                },
            })
        return {rule["rule_id"]: rule for rule in result["rules"]}

    normal = decision(False)
    exercise = decision(True)
    assert normal["HZ-019"]["active"] is False
    assert normal["HZ-020"]["active"] is False
    assert exercise["HZ-019"]["active"] is True
    assert exercise["HZ-020"]["active"] is True
