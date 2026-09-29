"""Continuous speed modes change wall-clock pacing, not simulation steps."""

import pytest

from h2station.simulation_clock import SimulationClock
from h2station.api import _position_live_fault
from h2station.safety_runtime import FaultEvent, FaultKind


def test_speed_changes_rebase_pacing_without_jumping_simulated_time():
    wall = [0.0]
    waits = []

    def wait(seconds):
        waits.append(seconds)
        wall[0] += seconds

    clock = SimulationClock(now=lambda: wall[0], wait=wait)
    clock.pace(0.0)
    clock.pace(1.0)
    assert waits[-1] == pytest.approx(1.0)

    clock.set_speed(10, 1.0)
    clock.pace(2.0)
    assert waits[-1] == pytest.approx(0.1)

    clock.set_speed(100, 2.0)
    clock.pace(3.0)
    assert waits[-1] == pytest.approx(0.01)
    assert clock.speed_multiplier == 100


def test_relative_fault_delay_is_measured_at_the_solver_step():
    event = FaultEvent("remote-delay", FaultKind.SENSOR_BIAS, "PT-1101",
                       start_time_s=5.0, end_time_s=20.0, magnitude=1.0)
    scheduled = _position_live_fault(event, time_s=317.2, relative=True)
    assert scheduled.start_time_s == pytest.approx(322.2)
    assert scheduled.end_time_s == pytest.approx(337.2)
    assert not scheduled.active_at(317.2)
