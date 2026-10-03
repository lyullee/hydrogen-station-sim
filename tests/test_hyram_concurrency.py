"""Native HyRAM physics calls must not overlap across independent monitors."""

from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from time import sleep
from types import SimpleNamespace

from h2station.risk.hyram_adapter import HyRAMRiskMonitor, LeakScenario


def test_native_physics_calls_are_serialized_across_monitors(monkeypatch):
    state = {"active": 0, "maximum": 0}
    counter_lock = Lock()

    def jet_flame_analysis(*args, **kwargs):
        with counter_lock:
            state["active"] += 1
            state["maximum"] = max(state["maximum"], state["active"])
        sleep(0.03)
        with counter_lock:
            state["active"] -= 1
        return (None, None, [], 0.001, None, 0.0, 0.0)

    fake_api = SimpleNamespace(create_fluid=lambda *args, **kwargs: object(),
                               jet_flame_analysis=jet_flame_analysis)
    monkeypatch.setattr(HyRAMRiskMonitor, "_physics_api", staticmethod(lambda: fake_api))
    release_state = SimpleNamespace(pressure=44e6, temperature=296.85)
    scenario = LeakScenario(
        orifice_diameter=0.001,
        locations=(),
        calculate_overpressure=False,
        calculate_dispersion=False,
    )

    def evaluate(_):
        monitor = HyRAMRiskMonitor()
        return monitor.evaluate(0.0, release_state, scenario, mass_flow_override=0.001)

    with ThreadPoolExecutor(max_workers=2) as pool:
        snapshots = list(pool.map(evaluate, range(2)))

    assert len(snapshots) == 2
    assert state["maximum"] == 1
