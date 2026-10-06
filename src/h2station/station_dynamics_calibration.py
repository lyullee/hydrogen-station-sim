"""Privacy-bounded station-side recharge dynamics calibration.

This module is deliberately narrower than a station-to-vehicle calibration.
It uses an owner-attested compressor-state signal with mapped storage-pressure
roles to quantify observed recharge dwell and pressure response.  Raw rows,
source columns, timestamps, and state values remain in memory and are never
included in the resulting aggregate artifact.

The output may be used to set an *opt-in* compressor restart dwell.  It must
not be used to infer compressor capacity, vessel volume, vehicle fueling
accuracy, failure frequency, or a safety limit without the corresponding
measured flow, geometry, and validation evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
from statistics import median
from typing import Iterable, Mapping

from .controlled_station_replay import (
    TraceMapping,
    _finite,
    _paths,
    _quantile,
    _sampled_rows,
)


def _state(value: object) -> str:
    return str(value or "").strip().casefold()


@dataclass(frozen=True)
class BankRechargeDynamicsSummary:
    """Aggregate response of one generically mapped storage role."""

    bank: str
    sampled_intervals: int
    active_interval_count: int
    positive_active_ramp_median_pa_s: float | None
    positive_active_ramp_p95_pa_s: float | None
    inactive_absolute_ramp_p95_pa_s: float | None
    recharge_cycle_count: int
    cycle_hysteresis_median_pa: float | None

    def to_public_dict(self) -> dict[str, object]:
        return {
            "bank": self.bank,
            "sampled_intervals": self.sampled_intervals,
            "active_interval_count": self.active_interval_count,
            "positive_active_ramp_median_pa_s": _rounded(
                self.positive_active_ramp_median_pa_s
            ),
            "positive_active_ramp_p95_pa_s": _rounded(
                self.positive_active_ramp_p95_pa_s
            ),
            "inactive_absolute_ramp_p95_pa_s": _rounded(
                self.inactive_absolute_ramp_p95_pa_s
            ),
            "recharge_cycle_count": self.recharge_cycle_count,
            "cycle_hysteresis_median_pa": _rounded(
                self.cycle_hysteresis_median_pa
            ),
        }


@dataclass(frozen=True)
class StationRechargeDynamicsSummary:
    """De-identified evidence for an optional compressor restart dwell."""

    files_read: int
    sampled_rows: int
    state_transition_count: int
    active_duty_cycle: float
    median_sample_period_s: float | None
    observed_off_to_on_intervals: int
    recommended_minimum_recharge_off_time_s: float | None
    bank_profiles: tuple[BankRechargeDynamicsSummary, ...]
    quality_warnings: tuple[str, ...]

    def to_public_dict(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "raw_rows_persisted": False,
            "source_identifiers_published": False,
            "absolute_timestamps_published": False,
            "files_read": self.files_read,
            "sampled_rows": self.sampled_rows,
            "state_transition_count": self.state_transition_count,
            "active_duty_cycle": round(self.active_duty_cycle, 6),
            "median_sample_period_s": _rounded(self.median_sample_period_s),
            "observed_off_to_on_intervals": self.observed_off_to_on_intervals,
            "recommended_minimum_recharge_off_time_s": _rounded(
                self.recommended_minimum_recharge_off_time_s
            ),
            "bank_profiles": [profile.to_public_dict() for profile in self.bank_profiles],
            "quality_warnings": list(self.quality_warnings),
            "claim_boundary": (
                "Owner-attested station-side compressor restart-dwell and "
                "storage-pressure response aggregate only; this is not a "
                "compressor-capacity fit, station-to-vehicle validation, "
                "safety limit, or field-safety certification."
            ),
        }


@dataclass(frozen=True)
class StationRechargeDynamicsHoldout:
    """Chronological check for a restart-dwell recommendation.

    The recommendation is fitted on the earlier portion of each trace.  The
    later portion is used only to check whether its observed completed OFF
    windows honour that dwell.  It is intentionally a narrow controller
    behavior check, never an accuracy claim for the station or vehicle model.
    """

    calibration: StationRechargeDynamicsSummary
    holdout_files: int
    holdout_sampled_rows: int
    holdout_completed_off_to_on_intervals: int
    holdout_minimum_off_to_on_s: float | None
    calibration_fraction: float
    dwell_consistent: bool
    quality_warnings: tuple[str, ...]

    def to_public_dict(self) -> dict[str, object]:
        return {
            "method": "chronological_within_trace_holdout",
            "calibration_fraction": round(self.calibration_fraction, 6),
            "holdout_files": self.holdout_files,
            "holdout_sampled_rows": self.holdout_sampled_rows,
            "holdout_completed_off_to_on_intervals": (
                self.holdout_completed_off_to_on_intervals
            ),
            "holdout_minimum_off_to_on_s": _rounded(
                self.holdout_minimum_off_to_on_s
            ),
            "dwell_consistent": self.dwell_consistent,
            "quality_warnings": list(self.quality_warnings),
            "claim_boundary": (
                "Chronological compressor restart-dwell consistency check only; "
                "not a station-to-vehicle prediction validation or safety limit."
            ),
        }


def _rounded(value: float | None) -> float | None:
    return round(float(value), 6) if value is not None and math.isfinite(value) else None


def _validated_bank_roles(
    mapping: TraceMapping,
    bank_by_pressure_role: Mapping[str, str],
) -> tuple[tuple[str, str], ...]:
    mapped_roles = {role for role, _ in mapping.pressure_columns}
    pairs = tuple((str(role), str(bank)) for role, bank in bank_by_pressure_role.items())
    if not pairs:
        raise ValueError("bank_by_pressure_role cannot be empty")
    if any(role not in mapped_roles for role, _ in pairs):
        raise ValueError("every bank role must reference a mapped pressure role")
    if any(bank not in {"low", "medium", "high"} for _, bank in pairs):
        raise ValueError("bank names must be low, medium, or high")
    if len({bank for _, bank in pairs}) != len(pairs):
        raise ValueError("each simulator bank may be mapped only once")
    return pairs


def _load_observations(
    input_path: Path,
    mapping: TraceMapping,
    *,
    role_order: tuple[str, ...],
    pressure_columns: Mapping[str, str],
    compressor_state_role: str,
    active_values: set[str],
    stride: int,
    max_rows_per_file: int | None,
) -> tuple[dict[Path, list[tuple[float, bool, dict[str, float]]]], int, int]:
    """Read restricted rows in memory and return no source metadata."""

    observations: dict[Path, list[tuple[float, bool, dict[str, float]]]] = {}
    files: set[Path] = set()
    sampled_rows = 0
    state_columns = dict(mapping.state_columns)
    for path, time_s, row in _sampled_rows(
        input_path, mapping, stride=stride, max_rows_per_file=max_rows_per_file
    ):
        files.add(path)
        sampled_rows += 1
        pressures: dict[str, float] = {}
        for role in role_order:
            value = _finite(row.get(pressure_columns[role]))
            if value is not None:
                pressure = value * mapping.pressure_scale_pa_per_unit
                if pressure > 0.0 and math.isfinite(pressure):
                    pressures[role] = pressure
        observations.setdefault(path, []).append(
            (
                float(time_s),
                _state(row.get(state_columns[compressor_state_role])) in active_values,
                pressures,
            )
        )
    return observations, len(files), sampled_rows


def _summarize_observations(
    observations: Mapping[Path, list[tuple[float, bool, dict[str, float]]]],
    *,
    role_pairs: tuple[tuple[str, str], ...],
    files_read: int,
    sampled_rows: int,
) -> tuple[StationRechargeDynamicsSummary, tuple[float, ...]]:
    """Reduce in-memory restricted rows to a de-identified summary."""

    if not observations:
        raise ValueError("no rows matched the station dynamics mapping")
    role_order = tuple(role for role, _ in role_pairs)
    bank_by_role = dict(role_pairs)
    active_seconds = 0.0
    sampled_seconds = 0.0
    transition_count = 0
    off_to_on_durations: list[float] = []
    intervals: list[float] = []
    active_ramps: dict[str, list[float]] = {role: [] for role in role_order}
    inactive_ramps: dict[str, list[float]] = {role: [] for role in role_order}
    cycle_hysteresis: dict[str, list[float]] = {role: [] for role in role_order}
    interval_count: dict[str, int] = {role: 0 for role in role_order}
    active_interval_count: dict[str, int] = {role: 0 for role in role_order}
    warnings: set[str] = set()

    for rows in observations.values():
        rows.sort(key=lambda item: item[0])
        if len(rows) < 2:
            warnings.add("insufficient_rows_in_trace")
            continue
        prior_time, prior_active, prior_pressures = rows[0]
        # A trace can begin while the compressor is already idle.  That first
        # OFF segment has an unknown start time, so it is not evidence of a
        # completed OFF-to-ON cycle and must not lower the restart dwell.
        off_started_s: float | None = None
        cycle_start_pressures: dict[str, float] | None = (
            dict(prior_pressures) if prior_active else None
        )
        for time_s, active, pressures in rows[1:]:
            dt = time_s - prior_time
            if dt <= 0.0:
                warnings.add("nonmonotonic_or_duplicate_time")
                prior_time, prior_active, prior_pressures = time_s, active, pressures
                continue
            intervals.append(dt)
            sampled_seconds += dt
            if prior_active:
                active_seconds += dt
            for role in role_order:
                before, after = prior_pressures.get(role), pressures.get(role)
                if before is None or after is None:
                    continue
                interval_count[role] += 1
                ramp = (after - before) / dt
                if prior_active:
                    active_interval_count[role] += 1
                    if ramp > 0.0:
                        active_ramps[role].append(ramp)
                else:
                    inactive_ramps[role].append(abs(ramp))
            if active != prior_active:
                transition_count += 1
                if active:
                    if off_started_s is not None:
                        off_to_on_durations.append(time_s - off_started_s)
                    cycle_start_pressures = dict(pressures)
                    off_started_s = None
                else:
                    if cycle_start_pressures is not None:
                        for role in role_order:
                            start = cycle_start_pressures.get(role)
                            stop = pressures.get(role)
                            if start is not None and stop is not None and stop >= start:
                                cycle_hysteresis[role].append(stop - start)
                    cycle_start_pressures = None
                    off_started_s = time_s
            prior_time, prior_active, prior_pressures = time_s, active, pressures

    if sampled_seconds <= 0.0:
        raise ValueError("station dynamics trace contains no positive time intervals")
    median_period = median(intervals) if intervals else None
    recommended_off = None
    if off_to_on_durations and median_period is not None:
        recommended_off = max(
            median_period,
            min(600.0, _quantile(sorted(off_to_on_durations), 0.10) or median_period),
        )
    profiles = tuple(
        BankRechargeDynamicsSummary(
            bank=bank_by_role[role],
            sampled_intervals=interval_count[role],
            active_interval_count=active_interval_count[role],
            positive_active_ramp_median_pa_s=(median(active_ramps[role]) if active_ramps[role] else None),
            positive_active_ramp_p95_pa_s=_quantile(sorted(active_ramps[role]), 0.95),
            inactive_absolute_ramp_p95_pa_s=_quantile(sorted(inactive_ramps[role]), 0.95),
            recharge_cycle_count=len(cycle_hysteresis[role]),
            cycle_hysteresis_median_pa=(median(cycle_hysteresis[role]) if cycle_hysteresis[role] else None),
        )
        for role in role_order
    )
    if not off_to_on_durations:
        warnings.add("no_completed_off_to_on_cycle")
    summary = StationRechargeDynamicsSummary(
        files_read=files_read,
        sampled_rows=sampled_rows,
        state_transition_count=transition_count,
        active_duty_cycle=active_seconds / sampled_seconds,
        median_sample_period_s=median_period,
        observed_off_to_on_intervals=len(off_to_on_durations),
        recommended_minimum_recharge_off_time_s=recommended_off,
        bank_profiles=profiles,
        quality_warnings=tuple(sorted(warnings)),
    )
    return summary, tuple(off_to_on_durations)


def summarize_recharge_dynamics(
    input_path: Path,
    mapping: TraceMapping,
    *,
    compressor_state_role: str,
    active_state_values: Iterable[str],
    bank_by_pressure_role: Mapping[str, str],
    pressure_semantics_attested: bool,
    state_semantics_attested: bool,
    stride: int = 1,
    max_rows_per_file: int | None = 250_000,
) -> StationRechargeDynamicsSummary:
    """Summarize owner-attested compressor cycles without writing raw data.

    ``active_state_values`` is deliberately supplied by the restricted mapping.
    The module never guesses which numeric or textual logger value means that a
    compressor is loaded.  Likewise, a pressure column must be mapped to the
    simulator's generic low/medium/high role by the data custodian.
    """

    if not pressure_semantics_attested:
        raise ValueError("pressure semantics attestation is required")
    if not state_semantics_attested:
        raise ValueError("compressor-state semantics attestation is required")
    if stride < 1:
        raise ValueError("stride must be at least one")
    if compressor_state_role not in dict(mapping.state_columns):
        raise ValueError("compressor_state_role must be present in mapping.state_columns")
    active_values = {_state(value) for value in active_state_values if _state(value)}
    if not active_values:
        raise ValueError("at least one active compressor-state value is required")
    role_pairs = _validated_bank_roles(mapping, bank_by_pressure_role)
    pressure_columns = dict(mapping.pressure_columns)
    role_order = tuple(role for role, _ in role_pairs)

    observations, files_read, sampled_rows = _load_observations(
        input_path,
        mapping,
        role_order=role_order,
        pressure_columns=pressure_columns,
        compressor_state_role=compressor_state_role,
        active_values=active_values,
        stride=stride,
        max_rows_per_file=max_rows_per_file,
    )
    summary, _ = _summarize_observations(
        observations,
        role_pairs=role_pairs,
        files_read=files_read,
        sampled_rows=sampled_rows,
    )
    return summary


def validate_recharge_dynamics_temporal_holdout(
    input_path: Path,
    mapping: TraceMapping,
    *,
    compressor_state_role: str,
    active_state_values: Iterable[str],
    bank_by_pressure_role: Mapping[str, str],
    pressure_semantics_attested: bool,
    state_semantics_attested: bool,
    calibration_fraction: float = 0.70,
    stride: int = 1,
    max_rows_per_file: int | None = 250_000,
) -> StationRechargeDynamicsHoldout:
    """Fit a dwell on chronological prefixes and test later trace segments.

    No raw point, source identifier, or timestamp is returned.  A holdout
    requires at least three complete OFF-to-ON intervals and every one must be
    no shorter than the fitted dwell before the artifact may be opted in.
    """

    if not 0.50 <= calibration_fraction < 0.90:
        raise ValueError("calibration_fraction must be in [0.50, 0.90)")
    if not pressure_semantics_attested:
        raise ValueError("pressure semantics attestation is required")
    if not state_semantics_attested:
        raise ValueError("compressor-state semantics attestation is required")
    if stride < 1:
        raise ValueError("stride must be at least one")
    if compressor_state_role not in dict(mapping.state_columns):
        raise ValueError("compressor_state_role must be present in mapping.state_columns")
    active_values = {_state(value) for value in active_state_values if _state(value)}
    if not active_values:
        raise ValueError("at least one active compressor-state value is required")
    role_pairs = _validated_bank_roles(mapping, bank_by_pressure_role)
    role_order = tuple(role for role, _ in role_pairs)
    observations, _, _ = _load_observations(
        input_path,
        mapping,
        role_order=role_order,
        pressure_columns=dict(mapping.pressure_columns),
        compressor_state_role=compressor_state_role,
        active_values=active_values,
        stride=stride,
        max_rows_per_file=max_rows_per_file,
    )
    calibration_rows: dict[Path, list[tuple[float, bool, dict[str, float]]]] = {}
    holdout_rows: dict[Path, list[tuple[float, bool, dict[str, float]]]] = {}
    warnings: set[str] = set()
    for path, rows in observations.items():
        ordered = sorted(rows, key=lambda item: item[0])
        split = int(len(ordered) * calibration_fraction)
        if split < 2 or len(ordered) - split < 2:
            warnings.add("insufficient_rows_for_temporal_split")
            continue
        calibration_rows[path] = ordered[:split]
        holdout_rows[path] = ordered[split:]
    calibration, _ = _summarize_observations(
        calibration_rows,
        role_pairs=role_pairs,
        files_read=len(calibration_rows),
        sampled_rows=sum(len(rows) for rows in calibration_rows.values()),
    )
    holdout, durations = _summarize_observations(
        holdout_rows,
        role_pairs=role_pairs,
        files_read=len(holdout_rows),
        sampled_rows=sum(len(rows) for rows in holdout_rows.values()),
    )
    recommendation = calibration.recommended_minimum_recharge_off_time_s
    minimum = min(durations) if durations else None
    if len(durations) < 3:
        warnings.add("insufficient_completed_holdout_cycles")
    if recommendation is None:
        warnings.add("no_calibration_dwell")
    if holdout.quality_warnings:
        warnings.update(f"holdout_{warning}" for warning in holdout.quality_warnings)
    dwell_consistent = bool(
        recommendation is not None
        and len(durations) >= 3
        and minimum is not None
        and minimum >= recommendation
        and not warnings
    )
    return StationRechargeDynamicsHoldout(
        calibration=calibration,
        holdout_files=len(holdout_rows),
        holdout_sampled_rows=sum(len(rows) for rows in holdout_rows.values()),
        holdout_completed_off_to_on_intervals=len(durations),
        holdout_minimum_off_to_on_s=minimum,
        calibration_fraction=calibration_fraction,
        dwell_consistent=dwell_consistent,
        quality_warnings=tuple(sorted(warnings)),
    )
