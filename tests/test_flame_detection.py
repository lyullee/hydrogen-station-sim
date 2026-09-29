from __future__ import annotations

from h2station.api import _analyze_frame
from h2station.hazop.database import load_catalog
from h2station.hazop.runtime import HazopMonitor
from h2station.risk.runtime_backend import UnavailableHyRAMBackend
from h2station.safety_runtime import FaultEvent, FaultKind
from h2station.scenario import ReferenceScenario, build_reference_scenario


def _simulate(faults=(), duration=1.2, virtual_detectors=True):
    built = build_reference_scenario(ReferenceScenario(fault_events=tuple(faults)),
                                     UnavailableHyRAMBackend())
    monitor = HazopMonitor(virtual_detectors=virtual_detectors)
    built.simulator.hazop_monitor = monitor
    built.simulator.simulate(built.initial_state, duration, .2)
    return monitor


def test_flame_catalog_and_normal_baseline():
    catalog = load_catalog()
    tags = {sensor["sensor_id"] for sensor in catalog["sensors"] if sensor["sensor_id"].startswith("FD-")}
    assert len(tags) == 9
    assert len([rule for rule in catalog["rules"] if rule["sensor_id"] in tags]) == 9
    monitor = _simulate(duration=.6)
    assert all(monitor.latest["signals"][tag]["value"] == 0 for tag in tags)
    assert not any(row["sensor_id"].startswith("FD-") for row in monitor.latest["active"])


def test_fire_input_waits_for_matching_virtual_flame_head():
    fire = FaultEvent("medium-fire", FaultKind.EXTERNAL_FIRE, "cascade.medium", 0,
                      external_temperature_k=900, heat_transfer_ua_w_k=100)
    monitor = _simulate([fire], 1.2)
    first = monitor.frames[0]["signals"]
    assert first["FD-0801"]["value"] == 0
    assert first["FD-0701"]["value"] == 0
    assert monitor.latest["signals"]["FD-0801"]["value"] == 1
    assert monitor.latest["signals"]["FD-0801"]["origin"] == "VIRTUAL_FLAME_DETECTOR_PROXY"
    assert monitor.latest["signals"]["FD-0701"]["value"] == 0
    assert [row["sensor_id"] for row in monitor.latest["active"] if row["sensor_id"].startswith("FD-")] == ["FD-0801"]


def test_fire_input_is_not_claimed_as_sensor_detection():
    pending = _analyze_frame({"active_faults": ["external-fire:cascade.medium"]})
    assert pending["fire_detection"]["status"] == "PENDING"
    assert "미확인" in " ".join(pending["findings"])
    detected = _analyze_frame({"active_faults": ["external-fire:cascade.medium"],
                               "flame_detectors": {"FD-0801": {"value": 1.0, "quality": "GOOD"}}})
    assert detected["fire_detection"]["status"] == "DETECTED"
    assert detected["fire_detection"]["detector_tags"] == ["FD-0801"]
    normal = _analyze_frame({"flame_detectors": {"FD-0801": {"value": 0.0, "quality": "GOOD"}}})
    assert normal["fire_detection"]["status"] == "NONE"
    assert normal["status"] == "NORMAL"


def test_no_proxy_signal_when_virtual_detection_disabled():
    fire = FaultEvent("medium-fire", FaultKind.EXTERNAL_FIRE, "cascade.medium", 0,
                      external_temperature_k=900, heat_transfer_ua_w_k=100)
    monitor = _simulate([fire], .6, virtual_detectors=False)
    assert "FD-0801" not in monitor.latest["signals"]
