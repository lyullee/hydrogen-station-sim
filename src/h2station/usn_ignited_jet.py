"""Safe reader for the public USN delayed-ignition jet CSV files.

The Dataverse files use a semicolon separator, decimal commas and two header
rows.  The raw pressure channels are voltage signals; the public README does
not provide enough information to infer each channel's physical sensor
position or a complete absolute-pressure calibration.  This module therefore
keeps raw voltages by default and requires an explicit calibration argument
before producing a pressure series.

It is an evidence-ingestion helper only.  It does not route runtime alarms,
change HyRAM parameters, or turn the laboratory experiment into an HRS or
station-to-vehicle validation claim.
"""

from __future__ import annotations

from dataclasses import dataclass
import csv
from pathlib import Path
from typing import Iterable, Iterator, Sequence

import numpy as np


PRESSURE_CHANNEL_COUNT = 4
EXPECTED_COLUMNS = 7


@dataclass(frozen=True, slots=True)
class IgnitedJetTrace:
    """Raw signals from one ``Ign_pipe_geom_EXP_*.csv`` file."""

    time_ms: np.ndarray
    trigger_v: np.ndarray
    pressure_channel_v: np.ndarray
    nozzle_pressure_v: np.ndarray

    @property
    def time_s(self) -> np.ndarray:
        return self.time_ms / 1000.0

    @property
    def row_count(self) -> int:
        return int(self.time_ms.size)


def _parse_decimal(value: str) -> float:
    """Parse the dataset's decimal-comma cells without locale mutation."""

    return float(value.strip().replace(",", "."))


def _iter_rows(path: str | Path) -> Iterator[tuple[float, ...]]:
    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle, delimiter=";")
        for row in reader:
            if not row or len(row) < EXPECTED_COLUMNS:
                continue
            # The first two rows are labels and units, not numeric samples.
            try:
                values = tuple(_parse_decimal(cell) for cell in row[:EXPECTED_COLUMNS])
            except (TypeError, ValueError):
                continue
            if all(np.isfinite(values)):
                yield values


def load_ignited_jet_csv(
    path: str | Path,
    *,
    max_rows: int | None = None,
) -> IgnitedJetTrace:
    """Load raw numeric channels while preserving source units and ordering.

    ``max_rows`` is intended for a bounded inspection, not a validation split.
    Duplicate or non-monotonic timestamps are retained so that a caller can
    make an explicit quality decision rather than silently changing evidence.
    """

    rows: list[tuple[float, ...]] = []
    for values in _iter_rows(path):
        rows.append(values)
        if max_rows is not None and len(rows) >= int(max_rows):
            break
    if not rows:
        raise ValueError("USN ignited-jet CSV contains no numeric rows")
    data = np.asarray(rows, dtype=float)
    return IgnitedJetTrace(
        time_ms=data[:, 0],
        trigger_v=data[:, 1],
        pressure_channel_v=data[:, 2:6],
        nozzle_pressure_v=data[:, 6],
    )


def summarize_raw_trace(trace: IgnitedJetTrace) -> dict[str, object]:
    """Return a calibration-neutral descriptive summary."""

    if trace.pressure_channel_v.shape[1] != PRESSURE_CHANNEL_COUNT:
        raise ValueError("expected four raw pressure channels")
    return {
        "rows": trace.row_count,
        "time_range_ms": [float(np.min(trace.time_ms)), float(np.max(trace.time_ms))],
        "time_strictly_increasing": bool(np.all(np.diff(trace.time_ms) > 0.0)),
        "pressure_channel_voltage_min": [
            float(value) for value in np.min(trace.pressure_channel_v, axis=0)
        ],
        "pressure_channel_voltage_max": [
            float(value) for value in np.max(trace.pressure_channel_v, axis=0)
        ],
        "nozzle_pressure_voltage_min": float(np.min(trace.nozzle_pressure_v)),
        "nozzle_pressure_voltage_max": float(np.max(trace.nozzle_pressure_v)),
        "calibration_applied": False,
    }


def calibrated_pressure_bar_g(
    raw_voltage_v: Sequence[float] | np.ndarray,
    *,
    bar_per_volt: float,
    zero_voltage_v: float = 0.0,
    sign: float = 1.0,
) -> np.ndarray:
    """Convert a raw channel only with an explicit, caller-supplied calibration.

    The function intentionally does not choose the USN README's example
    coefficients automatically: channel-specific zero and sign conventions
    must be confirmed from the raw-file metadata or custodian.
    """

    gain = float(bar_per_volt)
    zero = float(zero_voltage_v)
    direction = float(sign)
    if not np.isfinite(gain) or gain == 0.0:
        raise ValueError("bar_per_volt must be finite and non-zero")
    if not np.isfinite(zero) or not np.isfinite(direction) or direction == 0.0:
        raise ValueError("zero_voltage_v and sign must be finite; sign must be non-zero")
    values = np.asarray(raw_voltage_v, dtype=float)
    if values.ndim != 1 or not np.all(np.isfinite(values)):
        raise ValueError("raw_voltage_v must be a finite one-dimensional sequence")
    return direction * (values - zero) * gain


__all__ = [
    "EXPECTED_COLUMNS",
    "IgnitedJetTrace",
    "PRESSURE_CHANNEL_COUNT",
    "calibrated_pressure_bar_g",
    "load_ignited_jet_csv",
    "summarize_raw_trace",
]
