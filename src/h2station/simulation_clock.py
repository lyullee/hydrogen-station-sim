"""Wall-clock pacing for continuous simulation without changing solver time steps."""

from __future__ import annotations

from threading import Lock
from time import monotonic, sleep
from typing import Callable


class SimulationClock:
    def __init__(
        self,
        speed_multiplier: int = 1,
        *,
        now: Callable[[], float] = monotonic,
        wait: Callable[[float], None] = sleep,
    ) -> None:
        self._lock = Lock()
        self._now = now
        self._wait = wait
        self.speed_multiplier = speed_multiplier
        self._anchor_sim_s: float | None = None
        self._anchor_wall_s: float | None = None
        self._meter_sim_s: float | None = None
        self._meter_wall_s: float | None = None
        self._actual_rate_x: float | None = None

    def set_speed(self, multiplier: int, latest_sim_s: float) -> None:
        """Rebase the clock so changing speed never jumps the simulation time."""
        with self._lock:
            if self._anchor_wall_s is not None:
                wall = self._now()
                self._anchor_sim_s = latest_sim_s
                self._anchor_wall_s = wall
                self._meter_sim_s = latest_sim_s
                self._meter_wall_s = wall
                self._actual_rate_x = None
            self.speed_multiplier = multiplier

    def pace(self, simulated_time_s: float) -> tuple[float, float | None]:
        """Return wall-clock lag and measured speed after pacing this sample."""
        with self._lock:
            if self._anchor_wall_s is None:
                wall = self._now()
                self._anchor_sim_s = simulated_time_s
                self._anchor_wall_s = wall
                self._meter_sim_s = simulated_time_s
                self._meter_wall_s = wall
            speed = self.speed_multiplier
            anchor_sim = self._anchor_sim_s
            anchor_wall = self._anchor_wall_s
        target_wall = anchor_wall + (simulated_time_s - anchor_sim) / speed
        ahead_s = target_wall - self._now()
        if ahead_s > 0:
            self._wait(ahead_s)
        wall = self._now()
        with self._lock:
            # A speed change during the wait is applied from the next sample.
            if speed != self.speed_multiplier or anchor_wall != self._anchor_wall_s:
                return 0.0, self._actual_rate_x
            if simulated_time_s > self._meter_sim_s and wall > self._meter_wall_s:
                instant_rate = (simulated_time_s - self._meter_sim_s) / max(
                    wall - self._meter_wall_s, 1e-6
                )
                self._actual_rate_x = (instant_rate if self._actual_rate_x is None else
                                       0.7 * self._actual_rate_x + 0.3 * instant_rate)
                self._meter_sim_s = simulated_time_s
                self._meter_wall_s = wall
            return max(0.0, wall - target_wall), self._actual_rate_x
