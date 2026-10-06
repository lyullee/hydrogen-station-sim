"""Rights-gated ingestion for the public heavy-vehicle refuelling export.

The catalogue exposes a public description and a file tree, but the numerical
files require an approved download.  This module therefore accepts a local,
rights-cleared workbook only after the caller has recorded its provenance and
hash.  It never writes source rows, source filenames, timestamps, or source
identifiers to a repository artifact.

The NBS DC dataset contains test-cylinder traces.  They can be compared with
the vehicle-side model channels only when the custodian confirms the test
mapping; the loader deliberately does not promote them to station-to-vehicle
validation by itself.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import math
from pathlib import Path
from statistics import median
from typing import Iterable, Mapping

import numpy as np

from .validation import OutputChannel, ValidationTrace


_PRESSURE_SCALE = {"pa": 1.0, "kpa": 1.0e3, "mpa": 1.0e6, "bar": 1.0e5}
_TEMPERATURE_OFFSET = {"k": (1.0, 0.0), "c": (1.0, 273.15)}
_FLOW_SCALE = {"kg/s": 1.0, "kg/min": 1.0 / 60.0, "g/s": 1.0e-3, "g/min": 1.0e-3 / 60.0}
_MASS_SCALE = {"kg": 1.0, "g": 1.0e-3}


def _finite(value: object) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def _time_seconds(value: object) -> float | None:
    if isinstance(value, datetime):
        return value.timestamp()
    numeric = _finite(value)
    if numeric is not None:
        return numeric
    text = str(value or "").strip().replace("Z", "+00:00")
    if not text:
        return None
    try:
        return datetime.fromisoformat(text).timestamp()
    except ValueError:
        return None


def _normalise_unit(value: str, allowed: Mapping[str, float]) -> str:
    unit = str(value).strip().lower().replace(" ", "")
    if unit not in allowed:
        raise ValueError(f"unsupported unit {value!r}; expected one of {sorted(allowed)}")
    return unit


@dataclass(frozen=True)
class NbsdcColumnMap:
    """Explicit column and unit mapping supplied by the data custodian."""

    time: str
    pressure: str
    pressure_unit: str
    temperature: str | None = None
    temperature_unit: str = "C"
    mass_flow: str | None = None
    mass_flow_unit: str = "kg/s"
    transferred_mass: str | None = None
    transferred_mass_unit: str = "kg"

    def __post_init__(self) -> None:
        if not self.time or not self.pressure:
            raise ValueError("time and pressure columns are required")
        object.__setattr__(self, "pressure_unit", _normalise_unit(self.pressure_unit, _PRESSURE_SCALE))
        object.__setattr__(self, "temperature_unit", str(self.temperature_unit).strip().lower())
        if self.temperature is not None and self.temperature_unit not in _TEMPERATURE_OFFSET:
            raise ValueError("temperature_unit must be C or K")
        object.__setattr__(self, "mass_flow_unit", str(self.mass_flow_unit).strip().lower())
        if self.mass_flow is not None and self.mass_flow_unit not in _FLOW_SCALE:
            raise ValueError(f"unsupported mass_flow_unit {self.mass_flow_unit!r}")
        object.__setattr__(self, "transferred_mass_unit", str(self.transferred_mass_unit).strip().lower())
        if self.transferred_mass is not None and self.transferred_mass_unit not in _MASS_SCALE:
            raise ValueError(f"unsupported transferred_mass_unit {self.transferred_mass_unit!r}")


@dataclass(frozen=True)
class NbsdcRefuelTrace:
    """A sanitized in-memory trace from one approved workbook."""

    case_id: str
    source: str
    time_s: np.ndarray
    pressure_pa: np.ndarray
    temperature_k: np.ndarray | None = None
    mass_flow_kg_s: np.ndarray | None = None
    transferred_mass_kg: np.ndarray | None = None

    def __post_init__(self) -> None:
        time = np.asarray(self.time_s, dtype=float)
        pressure = np.asarray(self.pressure_pa, dtype=float)
        if len(time) < 2 or pressure.shape != time.shape:
            raise ValueError("trace requires at least two pressure samples")
        if np.any(~np.isfinite(time)) or np.any(~np.isfinite(pressure)):
            raise ValueError("time and pressure must be finite")
        if np.any(np.diff(time) <= 0.0):
            raise ValueError("time samples must be strictly increasing")
        if not self.case_id or not self.source:
            raise ValueError("case_id and source are required")
        object.__setattr__(self, "time_s", time)
        object.__setattr__(self, "pressure_pa", pressure)
        for name in ("temperature_k", "mass_flow_kg_s", "transferred_mass_kg"):
            values = getattr(self, name)
            if values is None:
                continue
            array = np.asarray(values, dtype=float)
            if array.shape != time.shape or np.any(~np.isfinite(array)):
                raise ValueError(f"{name} must be finite and aligned with time")
            object.__setattr__(self, name, array)

    @property
    def median_sample_period_s(self) -> float:
        return float(median(np.diff(self.time_s)))

    def summary(self) -> dict[str, object]:
        """Return only aggregate values suitable for a review artifact."""

        return {
            "case_id": self.case_id,
            "source": self.source,
            "sample_count": int(len(self.time_s)),
            "duration_s": float(self.time_s[-1] - self.time_s[0]),
            "median_sample_period_s": self.median_sample_period_s,
            "pressure_pa": {
                "min": float(np.min(self.pressure_pa)),
                "median": float(np.median(self.pressure_pa)),
                "max": float(np.max(self.pressure_pa)),
            },
            "has_temperature": self.temperature_k is not None,
            "has_mass_flow": self.mass_flow_kg_s is not None,
            "has_transferred_mass": self.transferred_mass_kg is not None,
        }

    def validation_traces(
        self,
        *,
        pressure_channel: OutputChannel = OutputChannel.VEHICLE_GAS_PRESSURE,
        temperature_channel: OutputChannel = OutputChannel.VEHICLE_GAS_TEMPERATURE,
        flow_channel: OutputChannel = OutputChannel.DISPENSED_MASS_FLOW,
    ) -> dict[OutputChannel, ValidationTrace]:
        """Map approved test channels to model channels without claiming equivalence."""

        traces = {
            pressure_channel: ValidationTrace(
                channel=pressure_channel,
                time_s=self.time_s,
                values=self.pressure_pa,
                unit="Pa",
                source=self.source,
                case_id=self.case_id,
            )
        }
        if self.temperature_k is not None:
            traces[temperature_channel] = ValidationTrace(
                channel=temperature_channel,
                time_s=self.time_s,
                values=self.temperature_k,
                unit="K",
                source=self.source,
                case_id=self.case_id,
            )
        if self.mass_flow_kg_s is not None:
            traces[flow_channel] = ValidationTrace(
                channel=flow_channel,
                time_s=self.time_s,
                values=self.mass_flow_kg_s,
                unit="kg/s",
                source=self.source,
                case_id=self.case_id,
            )
        return traces


def read_nbsdc_workbook(
    path: str | Path,
    mapping: NbsdcColumnMap,
    *,
    case_id: str,
    source: str,
    sheet_name: str | None = None,
    max_rows: int | None = None,
) -> NbsdcRefuelTrace:
    """Read one rights-cleared NBS DC workbook into memory.

    ``source`` is an approved opaque provenance label (for example an internal
    hash), never a site, operator, manufacturer, or exact date.  The loader
    rejects missing or duplicate timestamps rather than silently time-warping
    a logger trace.
    """

    try:
        from openpyxl import load_workbook
    except ImportError as exc:  # pragma: no cover - dependency is optional
        raise RuntimeError("openpyxl is required for NBS DC workbook intake") from exc
    workbook = load_workbook(filename=Path(path), read_only=True, data_only=True)
    try:
        sheet = workbook[sheet_name] if sheet_name else workbook.active
        rows = sheet.iter_rows(values_only=True)
        headers = tuple(str(item).strip() if item is not None else "" for item in next(rows))
        try:
            indexes = {
                name: headers.index(column)
                for name, column in {
                    "time": mapping.time,
                    "pressure": mapping.pressure,
                }.items()
            }
            for name, column in {
                "temperature": mapping.temperature,
                "mass_flow": mapping.mass_flow,
                "transferred_mass": mapping.transferred_mass,
            }.items():
                if column is not None:
                    indexes[name] = headers.index(column)
        except ValueError as exc:
            raise ValueError(f"mapped column is absent from workbook: {exc}") from exc

        records: list[tuple[float, float, float | None, float | None, float | None]] = []
        for row_number, row in enumerate(rows, start=2):
            if max_rows is not None and len(records) >= max_rows:
                break
            time = _time_seconds(row[indexes["time"]] if indexes["time"] < len(row) else None)
            pressure = _finite(row[indexes["pressure"]] if indexes["pressure"] < len(row) else None)
            if time is None or pressure is None:
                continue
            temperature = (
                _finite(row[indexes["temperature"]])
                if "temperature" in indexes and indexes["temperature"] < len(row) else None
            )
            mass_flow = (
                _finite(row[indexes["mass_flow"]])
                if "mass_flow" in indexes and indexes["mass_flow"] < len(row) else None
            )
            transferred_mass = (
                _finite(row[indexes["transferred_mass"]])
                if "transferred_mass" in indexes and indexes["transferred_mass"] < len(row) else None
            )
            records.append((time, pressure, temperature, mass_flow, transferred_mass))
    finally:
        workbook.close()

    if len(records) < 2:
        raise ValueError("workbook contains fewer than two usable samples")
    records.sort(key=lambda item: item[0])
    if any(right[0] == left[0] for left, right in zip(records, records[1:])):
        raise ValueError("duplicate timestamps require custodian-side resolution before intake")
    time = np.array([item[0] for item in records], dtype=float)
    pressure = np.array([item[1] * _PRESSURE_SCALE[mapping.pressure_unit] for item in records], dtype=float)

    def optional_values(index: int, scale: Mapping[str, float], unit: str) -> np.ndarray | None:
        raw = [item[index] for item in records]
        if not any(value is not None for value in raw):
            return None
        if any(value is None for value in raw):
            raise ValueError("optional channels must not contain partial missing values")
        return np.array([float(value) * scale[unit] for value in raw], dtype=float)

    temperature = None
    if mapping.temperature is not None:
        raw = [item[2] for item in records]
        if any(value is None for value in raw):
            raise ValueError("temperature channel contains missing values")
        factor, offset = _TEMPERATURE_OFFSET[mapping.temperature_unit]
        temperature = np.array([float(value) * factor + offset for value in raw], dtype=float)
    mass_flow = optional_values(3, _FLOW_SCALE, mapping.mass_flow_unit) if mapping.mass_flow else None
    transferred_mass = optional_values(4, _MASS_SCALE, mapping.transferred_mass_unit) if mapping.transferred_mass else None
    return NbsdcRefuelTrace(case_id, source, time - time[0], pressure, temperature, mass_flow, transferred_mass)


__all__ = ["NbsdcColumnMap", "NbsdcRefuelTrace", "read_nbsdc_workbook"]
