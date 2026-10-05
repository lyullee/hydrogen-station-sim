"""Privacy-preserving replay helpers for owner-controlled station traces.

The adapter deliberately keeps the raw archive outside the repository.  A
custodian-supplied mapping is required at runtime, and the public result is a
set of aggregate boundary parameters rather than a copy of the trace.  Numeric
channels are resampled only when the caller asks for it; discrete valve/ESD
states use forward fill and are never linearly interpolated.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import csv
from bisect import bisect_left, bisect_right
import math
from pathlib import Path
from statistics import median, quantiles
from typing import Iterable, Iterator, Mapping, Sequence


@dataclass(frozen=True)
class TraceMapping:
    """Map owner-approved source columns to generic station signals.

    The source column names are intentionally supplied by the caller instead
    of being embedded in the package.  This prevents proprietary tag names
    from becoming public code or documentation.
    """

    time_column: str | None = None
    time_column_index: int | None = None
    pressure_columns: tuple[tuple[str, str], ...] = ()
    temperature_columns: tuple[tuple[str, str], ...] = ()
    flow_column: str | None = None
    state_columns: tuple[tuple[str, str], ...] = ()
    # For a synchronized equipment logger, a temperature is injected into the
    # station boundary only when the custodian explicitly identifies its role
    # as the measured supply-gas boundary.  Other temperatures remain
    # diagnostic channels and are never silently treated as inlet gas.
    temperature_boundary_role: str | None = None
    pressure_scale_pa_per_unit: float = 1.0e6
    temperature_scale_k_per_unit: float = 1.0
    temperature_offset_k: float = 273.15
    flow_scale_kg_s_per_unit: float = 1.0
    time_format: str | None = None
    # A caller may explicitly attest that numeric timestamps are absolute
    # epochs.  Relative counters are rejected by the two-logger synchronizer.
    time_is_absolute: bool = False
    encoding: str = "utf-8-sig"

    def __post_init__(self) -> None:
        if not self.time_column and self.time_column_index is None:
            raise ValueError("time_column or time_column_index is required")
        if self.time_column_index is not None and self.time_column_index < 0:
            raise ValueError("time_column_index cannot be negative")
        if self.pressure_scale_pa_per_unit <= 0.0:
            raise ValueError("pressure scale must be positive")
        if self.temperature_scale_k_per_unit <= 0.0:
            raise ValueError("temperature scale must be positive")
        if self.flow_scale_kg_s_per_unit <= 0.0:
            raise ValueError("flow scale must be positive")
        if self.temperature_boundary_role is not None and not self.temperature_boundary_role:
            raise ValueError("temperature_boundary_role cannot be empty")


@dataclass(frozen=True)
class StationCalibrationSummary:
    """Aggregates safe to review without exporting raw trace rows."""

    files_read: int
    sampled_rows: int
    finite_rows: int
    duration_s: float
    median_sample_period_s: float | None
    maximum_gap_s: float | None
    pressure_min_pa: float | None
    pressure_median_pa: float | None
    pressure_max_pa: float | None
    pressure_noise_sigma_pa: float | None
    pressure_ramp_p95_pa_s: float | None
    flow_p95_kg_s: float | None
    recommended_recharge_hysteresis_pa: float | None
    recommended_recharge_restart_margin_pa: float | None
    channel_roles: tuple[str, ...]
    quality_warnings: tuple[str, ...]
    temperature_min_deg_c: float | None = None
    temperature_median_deg_c: float | None = None
    temperature_max_deg_c: float | None = None
    state_transition_count: int = 0

    def to_public_dict(self) -> dict[str, object]:
        """Return only de-identified aggregate calibration information."""

        return {
            "schema_version": 1,
            "raw_rows_persisted": False,
            "source_identifiers_published": False,
            "files_read": self.files_read,
            "sampled_rows": self.sampled_rows,
            "finite_rows": self.finite_rows,
            "duration_s": round(self.duration_s, 3),
            "median_sample_period_s": (
                round(self.median_sample_period_s, 3)
                if self.median_sample_period_s is not None else None
            ),
            "maximum_gap_s": (
                round(self.maximum_gap_s, 3)
                if self.maximum_gap_s is not None else None
            ),
            "boundary_pressure_pa": {
                "min": round(self.pressure_min_pa, 1)
                if self.pressure_min_pa is not None else None,
                "median": round(self.pressure_median_pa, 1)
                if self.pressure_median_pa is not None else None,
                "max": round(self.pressure_max_pa, 1)
                if self.pressure_max_pa is not None else None,
                "noise_sigma": round(self.pressure_noise_sigma_pa, 1)
                if self.pressure_noise_sigma_pa is not None else None,
                "positive_ramp_p95": round(self.pressure_ramp_p95_pa_s, 3)
                if self.pressure_ramp_p95_pa_s is not None else None,
            },
            "flow_p95_kg_s": (
                round(self.flow_p95_kg_s, 6)
                if self.flow_p95_kg_s is not None else None
            ),
            "boundary_temperature_degC": {
                "min": round(self.temperature_min_deg_c, 3)
                if self.temperature_min_deg_c is not None else None,
                "median": round(self.temperature_median_deg_c, 3)
                if self.temperature_median_deg_c is not None else None,
                "max": round(self.temperature_max_deg_c, 3)
                if self.temperature_max_deg_c is not None else None,
            },
            "state_transition_count": self.state_transition_count,
            "recharge_hysteresis_pa": (
                round(self.recommended_recharge_hysteresis_pa, 1)
                if self.recommended_recharge_hysteresis_pa is not None else None
            ),
            "recharge_restart_margin_pa": (
                round(self.recommended_recharge_restart_margin_pa, 1)
                if self.recommended_recharge_restart_margin_pa is not None else None
            ),
            "channel_roles": list(self.channel_roles),
            "quality_warnings": list(self.quality_warnings),
            "claim_boundary": (
                "Aggregate station-boundary calibration only; this is not a "
                "full station-to-vehicle validation result."
            ),
        }


@dataclass(frozen=True)
class StationBoundaryProfile:
    """In-memory measured boundary profile for a controlled partial replay."""

    time_s: tuple[float, ...]
    pressure_pa: tuple[float, ...]
    temperature_k: tuple[float, ...] = ()

    def __post_init__(self) -> None:
        if len(self.time_s) != len(self.pressure_pa) or not self.time_s:
            raise ValueError("boundary profile requires equal non-empty time and pressure arrays")
        if self.temperature_k and len(self.temperature_k) != len(self.time_s):
            raise ValueError("temperature profile length must match time profile")
        if any(right <= left for left, right in zip(self.time_s, self.time_s[1:])):
            raise ValueError("boundary profile time must be strictly increasing")

    def reference_scenario_kwargs(self) -> dict[str, tuple[tuple[float, float], ...]]:
        """Return only the profile fields accepted by ``ReferenceScenario``."""

        result: dict[str, tuple[tuple[float, float], ...]] = {
            "supply_pressure_profile_pa": tuple(zip(self.time_s, self.pressure_pa)),
        }
        if self.temperature_k:
            result["supply_temperature_profile_k"] = tuple(zip(self.time_s, self.temperature_k))
        return result


@dataclass(frozen=True)
class TraceAlignmentSummary:
    """De-identified quality summary for a two-logger alignment attempt."""

    pressure_rows: int
    equipment_rows: int
    synchronized_rows: int
    overlap_duration_s: float
    median_nearest_gap_s: float | None
    maximum_nearest_gap_s: float | None
    state_transition_count: int
    quality_warnings: tuple[str, ...]

    def to_public_dict(self) -> dict[str, object]:
        """Expose alignment quality without paths, tags, timestamps, or rows."""

        return {
            "schema_version": 1,
            "raw_rows_persisted": False,
            "source_identifiers_published": False,
            "pressure_rows": self.pressure_rows,
            "equipment_rows": self.equipment_rows,
            "synchronized_rows": self.synchronized_rows,
            "overlap_duration_s": round(self.overlap_duration_s, 3),
            "median_nearest_gap_s": (
                round(self.median_nearest_gap_s, 3)
                if self.median_nearest_gap_s is not None else None
            ),
            "maximum_nearest_gap_s": (
                round(self.maximum_nearest_gap_s, 3)
                if self.maximum_nearest_gap_s is not None else None
            ),
            "state_transition_count": self.state_transition_count,
            "quality_warnings": list(self.quality_warnings),
            "claim_boundary": (
                "Controlled logger alignment summary only; this is not a "
                "full station-to-vehicle validation result."
            ),
        }


@dataclass(frozen=True)
class SynchronizedStationProfile:
    """Pressure boundary plus nearest-time equipment observations.

    The object is intentionally in-memory only.  Equipment and state channels
    are kept as generic role/value tuples so a caller can feed an approved
    subset into a model without publishing proprietary tag names.
    """

    boundary: StationBoundaryProfile
    equipment_values: tuple[tuple[str, tuple[float, ...]], ...]
    state_values: tuple[tuple[str, tuple[str, ...]], ...]
    alignment: TraceAlignmentSummary

    def reference_scenario_kwargs(self) -> dict[str, tuple[tuple[float, float], ...]]:
        return self.boundary.reference_scenario_kwargs()


def _finite(value: object) -> float | None:
    try:
        result = float(str(value).strip())
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _time_seconds(value: object, mapping: TraceMapping, fallback: float) -> float:
    numeric = _finite(value)
    if numeric is not None:
        return numeric
    text = str(value).strip()
    if mapping.time_format:
        return datetime.strptime(text, mapping.time_format).timestamp()
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return fallback


def _paths(input_path: Path) -> list[Path]:
    if input_path.is_file():
        return [input_path]
    if input_path.is_dir():
        return sorted(
            path for path in input_path.rglob("*")
            if path.is_file() and path.suffix.lower() in {".csv", ".txt"}
        )
    raise FileNotFoundError(input_path)


def _sampled_rows(
    input_path: Path,
    mapping: TraceMapping,
    *,
    stride: int = 1,
    max_rows_per_file: int | None = None,
) -> Iterator[tuple[Path, float, dict[str, str]]]:
    if stride < 1:
        raise ValueError("stride must be at least one")
    for path in _paths(input_path):
        with path.open("r", encoding=mapping.encoding, errors="replace", newline="") as handle:
            reader = csv.DictReader(handle)
            fieldnames = tuple(reader.fieldnames or ())
            if mapping.time_column_index is not None:
                if mapping.time_column_index >= len(fieldnames):
                    raise ValueError(f"mapped time column index is absent from {path.name}")
                time_column = fieldnames[mapping.time_column_index]
            elif mapping.time_column in fieldnames:
                time_column = mapping.time_column
            else:
                raise ValueError(f"mapped time column is absent from {path.name}")
            emitted = 0
            fallback = 0.0
            for row_index, row in enumerate(reader):
                if row_index % stride:
                    fallback += 1.0
                    continue
                if max_rows_per_file is not None and emitted >= max_rows_per_file:
                    break
                yield path, _time_seconds(row.get(time_column), mapping, fallback), row
                emitted += 1
                fallback += float(stride)


def _collect_trace_points(
    input_path: Path,
    mapping: TraceMapping,
    *,
    stride: int,
    max_rows: int | None,
) -> list[tuple[float, float | None, dict[str, float], dict[str, str]]]:
    """Collect only mapped numeric/state values for one controlled trace."""

    paths = _paths(input_path)
    if len(paths) != 1:
        raise ValueError("trace synchronization requires exactly one private trace file per logger")
    points: list[tuple[float, float | None, dict[str, float], dict[str, str]]] = []
    for _, time_value, row in _sampled_rows(
        paths[0], mapping, stride=stride, max_rows_per_file=max_rows
    ):
        pressure_values = [
            value * mapping.pressure_scale_pa_per_unit
            for _, column in mapping.pressure_columns
            if (value := _finite(row.get(column))) is not None
        ]
        temperature_values: dict[str, float] = {}
        for role, column in mapping.temperature_columns:
            value = _finite(row.get(column))
            if value is not None:
                temperature_values[role] = (
                    value * mapping.temperature_scale_k_per_unit
                    + mapping.temperature_offset_k
                )
        state_values = {
            role: str(row.get(column, "")).strip()
            for role, column in mapping.state_columns
            if str(row.get(column, "")).strip()
        }
        if pressure_values or temperature_values or state_values:
            points.append(
                (
                    time_value,
                    float(median(pressure_values)) if pressure_values else None,
                    temperature_values,
                    state_values,
                )
            )
    points.sort(key=lambda item: item[0])
    return points


def synchronize_station_traces(
    pressure_input_path: Path,
    pressure_mapping: TraceMapping,
    equipment_input_path: Path,
    equipment_mapping: TraceMapping,
    *,
    stride: int = 1,
    max_rows: int | None = 100_000,
    max_match_gap_s: float = 2.0,
) -> SynchronizedStationProfile:
    """Align two owner-approved logger files on a relative time axis.

    The function requires an actual absolute-time overlap.  It never aligns
    unrelated campaigns by resetting both starts to zero, which would create
    a false synchronized validation set.  Numeric channels use nearest-time
    matching; discrete states are carried from the nearest observed sample
    and are never linearly interpolated.  Raw rows and absolute timestamps
    remain in memory only.
    """

    if max_match_gap_s <= 0.0:
        raise ValueError("max_match_gap_s must be positive")
    if not (pressure_mapping.time_format or pressure_mapping.time_is_absolute):
        raise ValueError("pressure mapping requires an absolute time format or attestation")
    if not (equipment_mapping.time_format or equipment_mapping.time_is_absolute):
        raise ValueError("equipment mapping requires an absolute time format or attestation")
    pressure_points = _collect_trace_points(
        pressure_input_path, pressure_mapping, stride=stride, max_rows=max_rows
    )
    equipment_points = _collect_trace_points(
        equipment_input_path, equipment_mapping, stride=stride, max_rows=max_rows
    )
    if not pressure_points or not equipment_points:
        raise ValueError("both logger traces require finite mapped observations")
    pressure_times = [item[0] for item in pressure_points]
    equipment_times = [item[0] for item in equipment_points]
    overlap_start = max(pressure_times[0], equipment_times[0])
    overlap_end = min(pressure_times[-1], equipment_times[-1])
    if overlap_end <= overlap_start:
        raise ValueError("logger time windows do not overlap")

    pressure_in_overlap = [
        item for item in pressure_points if overlap_start <= item[0] <= overlap_end
    ]
    if not pressure_in_overlap:
        raise ValueError("no pressure observations fall inside the logger overlap")
    equipment_roles = tuple(
        sorted({role for _, _, values, _ in equipment_points for role in values})
    )
    state_roles = tuple(
        sorted({role for _, _, _, values in equipment_points for role in values})
    )
    aligned_times: list[float] = []
    aligned_pressure: list[float] = []
    aligned_temperature: dict[str, list[float]] = {role: [] for role in equipment_roles}
    aligned_states: dict[str, list[str]] = {role: [] for role in state_roles}
    nearest_gaps: list[float] = []
    duplicate_time = False
    for pressure_time, pressure, _, _ in pressure_in_overlap:
        if pressure is None:
            continue
        position = bisect_left(equipment_times, pressure_time)
        candidates = []
        if position < len(equipment_points):
            candidates.append(equipment_points[position])
        if position:
            candidates.append(equipment_points[position - 1])
        nearest = min(candidates, key=lambda item: abs(item[0] - pressure_time))
        gap = abs(nearest[0] - pressure_time)
        if gap > max_match_gap_s:
            continue
        relative_time = float(pressure_time - overlap_start)
        if aligned_times and relative_time <= aligned_times[-1]:
            # Duplicate logger timestamps do not define a unique replay point.
            # Keep the first observation and record the quality issue.
            duplicate_time = True
            continue
        nearest_gaps.append(gap)
        aligned_times.append(relative_time)
        aligned_pressure.append(float(pressure))
        for role in equipment_roles:
            aligned_temperature[role].append(nearest[2].get(role, math.nan))
        state_position = bisect_right(equipment_times, pressure_time) - 1
        if state_position < 0:
            state_position = 0
        state_source = equipment_points[state_position]
        for role in state_roles:
            # Discrete controls use the most recent observed state; unlike
            # numeric channels they are never interpolated or averaged.
            aligned_states[role].append(state_source[3].get(role, ""))
    if not aligned_pressure:
        raise ValueError("no logger samples are within max_match_gap_s")

    warnings: set[str] = set()
    if duplicate_time:
        warnings.add("duplicate_or_nonmonotonic_pressure_time")
    coverage = len(aligned_pressure) / max(1, len(pressure_in_overlap))
    if coverage < 0.9:
        warnings.add("synchronization_coverage_below_90_percent")
    transition_count = 0
    for values in aligned_states.values():
        previous = None
        for value in values:
            if previous is not None and value != previous:
                transition_count += 1
            previous = value
    # A missing or unclassified channel is not fabricated.  Only a role
    # explicitly attested as the supply-gas boundary becomes a scenario
    # temperature profile; equipment temperatures remain diagnostic values.
    complete_temperature = ()
    if equipment_mapping.temperature_boundary_role is not None:
        candidate = aligned_temperature.get(equipment_mapping.temperature_boundary_role, [])
        if candidate and all(math.isfinite(value) for value in candidate):
            complete_temperature = tuple(candidate)
    boundary = StationBoundaryProfile(
        tuple(aligned_times), tuple(aligned_pressure), complete_temperature
    )
    alignment = TraceAlignmentSummary(
        pressure_rows=len(pressure_points),
        equipment_rows=len(equipment_points),
        synchronized_rows=len(aligned_pressure),
        overlap_duration_s=overlap_end - overlap_start,
        median_nearest_gap_s=median(nearest_gaps) if nearest_gaps else None,
        maximum_nearest_gap_s=max(nearest_gaps) if nearest_gaps else None,
        state_transition_count=transition_count,
        quality_warnings=tuple(sorted(warnings)),
    )
    numeric_values = tuple(
        (role, tuple(values))
        for role, values in aligned_temperature.items()
        if any(math.isfinite(value) for value in values)
    )
    discrete_values = tuple(
        (role, tuple(values))
        for role, values in aligned_states.items()
        if any(values)
    )
    return SynchronizedStationProfile(boundary, numeric_values, discrete_values, alignment)


def _quantile(values: Sequence[float], fraction: float) -> float | None:
    if not values:
        return None
    if len(values) == 1:
        return float(values[0])
    return float(quantiles(values, n=100, method="inclusive")[max(0, min(99, int(fraction * 100) - 1))])


def fit_station_boundary_profile(
    profile: StationBoundaryProfile,
    *,
    quality_warnings: Sequence[str] = (),
) -> StationCalibrationSummary:
    """Fit aggregate boundary calibration from an in-memory time slice.

    This helper is used by the private holdout runner.  The caller decides
    the calibration slice before the untouched replay slice is evaluated, so
    the fit cannot inspect a later model outcome.  Only aggregate statistics
    are returned; timestamps and samples remain in memory.
    """

    if len(profile.time_s) < 2:
        raise ValueError("boundary profile requires at least two points")
    intervals: list[float] = []
    pressure_steps: list[float] = []
    positive_ramps: list[float] = []
    for previous_time, time_s, previous_pressure, pressure in zip(
        profile.time_s,
        profile.time_s[1:],
        profile.pressure_pa,
        profile.pressure_pa[1:],
    ):
        dt = float(time_s - previous_time)
        if dt <= 0.0:
            raise ValueError("boundary profile time must be strictly increasing")
        step = float(pressure - previous_pressure)
        intervals.append(dt)
        pressure_steps.append(step)
        if step > 0.0:
            positive_ramps.append(step / dt)
    absolute_steps = [abs(value) for value in pressure_steps if abs(value) > 0.0]
    centered = [value - median(pressure_steps) for value in pressure_steps]
    noise_sigma = math.sqrt(sum(value * value for value in centered) / len(centered))
    stable_deltas = [
        value for value in absolute_steps
        if value <= (_quantile(absolute_steps, 0.75) or value)
    ]
    hysteresis = max(
        0.25e6,
        min(2.0e6, (_quantile(stable_deltas, 0.95) or 0.0) * 2.0),
    )
    temperatures = [value - 273.15 for value in profile.temperature_k if math.isfinite(value)]
    return StationCalibrationSummary(
        files_read=1,
        sampled_rows=len(profile.time_s),
        finite_rows=len(profile.pressure_pa),
        duration_s=float(profile.time_s[-1] - profile.time_s[0]),
        median_sample_period_s=median(intervals),
        maximum_gap_s=max(intervals),
        pressure_min_pa=min(profile.pressure_pa),
        pressure_median_pa=median(profile.pressure_pa),
        pressure_max_pa=max(profile.pressure_pa),
        pressure_noise_sigma_pa=noise_sigma,
        pressure_ramp_p95_pa_s=_quantile(positive_ramps, 0.95),
        flow_p95_kg_s=None,
        recommended_recharge_hysteresis_pa=hysteresis,
        recommended_recharge_restart_margin_pa=hysteresis,
        channel_roles=("station_pressure", "station_temperature")
        if temperatures else ("station_pressure",),
        quality_warnings=tuple(sorted(set(quality_warnings))),
        temperature_min_deg_c=min(temperatures) if temperatures else None,
        temperature_median_deg_c=median(temperatures) if temperatures else None,
        temperature_max_deg_c=max(temperatures) if temperatures else None,
        state_transition_count=0,
    )


def read_boundary_profile(
    input_path: Path,
    mapping: TraceMapping,
    *,
    stride: int = 1,
    max_rows: int | None = 100_000,
) -> StationBoundaryProfile:
    """Load one private trace into an in-memory relative-time profile.

    This helper is intended for a controlled partial-station replay. It does
    not write rows or timestamps to disk and rejects multi-file bundles so a
    caller cannot silently splice unrelated campaigns together.
    """

    paths = _paths(input_path)
    if len(paths) != 1:
        raise ValueError("read_boundary_profile requires exactly one private trace file")
    rows: list[tuple[float, float, float | None]] = []
    for path, time_value, row in _sampled_rows(
        paths[0], mapping, stride=stride, max_rows_per_file=max_rows
    ):
        values = [
            value * mapping.pressure_scale_pa_per_unit
            for _, column in mapping.pressure_columns
            if (value := _finite(row.get(column))) is not None
        ]
        if not values:
            continue
        temperature_values = [
            value * mapping.temperature_scale_k_per_unit + mapping.temperature_offset_k
            for _, column in mapping.temperature_columns
            if (value := _finite(row.get(column))) is not None
        ]
        rows.append((time_value, float(median(values)), median(temperature_values) if temperature_values else None))
    if not rows:
        raise ValueError("no finite pressure rows matched the mapping")
    # Source exports may be newest-first. Sorting occurs only in memory and
    # preserves a relative time axis with no identifying calendar timestamps.
    rows.sort(key=lambda item: item[0])
    origin = rows[0][0]
    times = tuple(float(time - origin) for time, _, _ in rows)
    pressures = tuple(float(pressure) for _, pressure, _ in rows)
    temperatures = tuple(
        float(value) if value is not None else math.nan for _, _, value in rows
    )
    if any(not math.isfinite(value) for value in temperatures):
        temperatures = ()
    return StationBoundaryProfile(times, pressures, temperatures)


def fit_station_boundary(
    input_path: Path,
    mapping: TraceMapping,
    *,
    stride: int = 60,
    max_rows_per_file: int | None = 250_000,
) -> StationCalibrationSummary:
    """Fit global station-boundary aggregates from a private trace bundle.

    The function reads rows in a streaming fashion and retains only numeric
    aggregates and a bounded sampled derivative history.  It never writes the
    input path, filenames, timestamps, or source column names to its result.
    """

    files: set[Path] = set()
    times: list[float] = []
    pressures: list[float] = []
    flows: list[float] = []
    pressure_steps: list[float] = []
    positive_ramps: list[float] = []
    temperatures: list[float] = []
    intervals: list[float] = []
    previous_by_file: dict[Path, tuple[float, float]] = {}
    direction_by_file: dict[Path, int] = {}
    previous_states_by_file: dict[Path, dict[str, str]] = {}
    state_transition_count = 0
    warnings: set[str] = set()

    for path, time_value, row in _sampled_rows(
        input_path, mapping, stride=stride, max_rows_per_file=max_rows_per_file
    ):
        files.add(path)
        pressure_values = [
            value * mapping.pressure_scale_pa_per_unit
            for _, column in mapping.pressure_columns
            if (value := _finite(row.get(column))) is not None
        ]
        if not pressure_values:
            warnings.add("rows_without_finite_pressure")
            continue
        pressure = float(median(pressure_values))
        times.append(time_value)
        pressures.append(pressure)
        if mapping.flow_column:
            flow = _finite(row.get(mapping.flow_column))
            if flow is not None:
                flows.append(max(0.0, flow * mapping.flow_scale_kg_s_per_unit))
        for _, column in mapping.temperature_columns:
            value = _finite(row.get(column))
            if value is not None:
                temperatures.append(
                    value * mapping.temperature_scale_k_per_unit
                    + mapping.temperature_offset_k - 273.15
                )
        if mapping.state_columns:
            previous_states = previous_states_by_file.setdefault(path, {})
            for role, column in mapping.state_columns:
                value = str(row.get(column, "")).strip()
                if role in previous_states and value != previous_states[role]:
                    state_transition_count += 1
                previous_states[role] = value
        previous = previous_by_file.get(path)
        if previous is not None:
            previous_time, previous_pressure = previous
            dt = time_value - previous_time
            if dt > 0.0:
                direction = direction_by_file.setdefault(path, 1)
                if direction != 1:
                    warnings.add("time_direction_changed")
                step = pressure - previous_pressure
                pressure_steps.append(step)
                if step > 0.0:
                    positive_ramps.append(step / dt)
                intervals.append(dt)
            elif dt < 0.0:
                direction = direction_by_file.setdefault(path, -1)
                if direction != -1:
                    warnings.add("time_direction_changed")
                # Some controller exports are newest-first.  Convert each
                # adjacent pair into chronological order without rewriting
                # the source file or exposing its timestamps.
                chronological_dt = -dt
                chronological_step = previous_pressure - pressure
                pressure_steps.append(chronological_step)
                if chronological_step > 0.0:
                    positive_ramps.append(chronological_step / chronological_dt)
                intervals.append(chronological_dt)
            else:
                warnings.add("duplicate_time")
        previous_by_file[path] = (time_value, pressure)

    if not pressures:
        raise ValueError("no finite pressure rows matched the mapping")
    positive_deltas = [abs(value) for value in pressure_steps if abs(value) > 0.0]
    noise_sigma = None
    if pressure_steps:
        centered = [value - median(pressure_steps) for value in pressure_steps]
        noise_sigma = math.sqrt(sum(value * value for value in centered) / len(centered))
    # Large pressure moves are operating events, not controller chatter.  Use
    # only the lower three quartiles to estimate a restart margin and cap the
    # result so a single trip or long logger gap cannot suppress recharge.
    stable_deltas = [
        value for value in positive_deltas
        if value <= (_quantile(positive_deltas, 0.75) or value)
    ]
    hysteresis = max(
        0.25e6,
        min(2.0e6, (_quantile(stable_deltas, 0.95) or 0.0) * 2.0),
    )
    return StationCalibrationSummary(
        files_read=len(files),
        sampled_rows=len(times),
        finite_rows=len(pressures),
        duration_s=max(times) - min(times) if len(times) > 1 else 0.0,
        median_sample_period_s=median(intervals) if intervals else None,
        maximum_gap_s=max(intervals) if intervals else None,
        pressure_min_pa=min(pressures),
        pressure_median_pa=median(pressures),
        pressure_max_pa=max(pressures),
        pressure_noise_sigma_pa=noise_sigma,
        pressure_ramp_p95_pa_s=_quantile(positive_ramps, 0.95),
        flow_p95_kg_s=_quantile(flows, 0.95),
        recommended_recharge_hysteresis_pa=hysteresis,
        recommended_recharge_restart_margin_pa=hysteresis,
        channel_roles=tuple(
            role for role, enabled in (
                ("station_pressure", bool(mapping.pressure_columns)),
                ("station_temperature", bool(mapping.temperature_columns)),
                ("mass_flow", mapping.flow_column is not None),
                ("discrete_state", bool(mapping.state_columns)),
            ) if enabled
        ),
        quality_warnings=tuple(sorted(warnings)),
        temperature_min_deg_c=min(temperatures) if temperatures else None,
        temperature_median_deg_c=median(temperatures) if temperatures else None,
        temperature_max_deg_c=max(temperatures) if temperatures else None,
        state_transition_count=state_transition_count,
    )


def apply_recharge_hysteresis(
    configured_margin_pa: float,
    calibration: StationCalibrationSummary,
) -> float:
    """Return a safe runtime margin without mutating caller configuration."""

    if configured_margin_pa <= 0.0:
        raise ValueError("configured_margin_pa must be positive")
    if calibration.recommended_recharge_restart_margin_pa is None:
        return configured_margin_pa
    return max(configured_margin_pa, calibration.recommended_recharge_restart_margin_pa)
