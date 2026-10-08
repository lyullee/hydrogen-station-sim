"""Privacy-bounded holdout for station storage-pressure cycling.

The source archive and its column mapping stay outside the repository.  Only
owner-attested generic roles are evaluated, and the public result contains no
paths, filenames, headers, timestamps, dates, tags or raw rows.
"""

from __future__ import annotations

from dataclasses import dataclass
import csv
import math
from pathlib import Path
from statistics import median
from typing import Mapping

from .confidential_history_profile import _read_header, header_fingerprint
from .confidential_signal_consistency import _parse_time
from .controlled_station_replay import _quantile


@dataclass(frozen=True, slots=True)
class PressureCycle:
    peak_time_s: float
    trough_time_s: float
    peak_pressure_mpa: float
    trough_pressure_mpa: float

    @property
    def pressure_drop_mpa(self) -> float:
        return self.peak_pressure_mpa - self.trough_pressure_mpa

    @property
    def decline_duration_s(self) -> float:
        return self.trough_time_s - self.peak_time_s


@dataclass(frozen=True, slots=True)
class PressureCycleRules:
    sample_stride: int = 10
    fall_confirmation_mpa: float = 0.25
    rise_confirmation_mpa: float = 0.25
    minimum_cycle_drop_mpa: float = 0.50
    maximum_cycle_drop_mpa: float = 20.0
    minimum_decline_duration_s: float = 30.0
    maximum_decline_duration_s: float = 21_600.0
    minimum_pressure_mpa: float = 10.0
    maximum_pressure_mpa: float = 100.0
    maximum_sample_gap_s: float = 120.0
    calibration_fraction: float = 0.70

    def __post_init__(self) -> None:
        positive = (
            self.sample_stride,
            self.fall_confirmation_mpa,
            self.rise_confirmation_mpa,
            self.minimum_cycle_drop_mpa,
            self.maximum_cycle_drop_mpa,
            self.minimum_decline_duration_s,
            self.maximum_decline_duration_s,
            self.minimum_pressure_mpa,
            self.maximum_pressure_mpa,
            self.maximum_sample_gap_s,
        )
        if any(not math.isfinite(float(value)) or float(value) <= 0.0 for value in positive):
            raise ValueError("pressure-cycle rules must be positive and finite")
        if self.maximum_cycle_drop_mpa <= self.minimum_cycle_drop_mpa:
            raise ValueError("maximum cycle drop must exceed the minimum")
        if self.maximum_decline_duration_s <= self.minimum_decline_duration_s:
            raise ValueError("maximum decline duration must exceed the minimum")
        if self.maximum_pressure_mpa <= self.minimum_pressure_mpa:
            raise ValueError("maximum pressure must exceed the minimum")
        if not 0.5 <= self.calibration_fraction < 1.0:
            raise ValueError("calibration fraction must be in [0.5, 1.0)")


class _CycleDetector:
    def __init__(self, rules: PressureCycleRules) -> None:
        self.rules = rules
        self.peak_time_s: float | None = None
        self.peak_pressure_mpa: float | None = None
        self.trough_time_s: float | None = None
        self.trough_pressure_mpa: float | None = None
        self.previous_time_s: float | None = None
        self.falling = False
        self.cycles: list[PressureCycle] = []

    def _reset(self, time_s: float, pressure_mpa: float) -> None:
        self.peak_time_s = time_s
        self.peak_pressure_mpa = pressure_mpa
        self.trough_time_s = None
        self.trough_pressure_mpa = None
        self.previous_time_s = time_s
        self.falling = False

    def add(self, time_s: float, pressure_mpa: float) -> None:
        if not (
            math.isfinite(time_s)
            and math.isfinite(pressure_mpa)
            and self.rules.minimum_pressure_mpa
            <= pressure_mpa
            <= self.rules.maximum_pressure_mpa
        ):
            self.peak_time_s = None
            self.previous_time_s = None
            self.falling = False
            return
        if (
            self.previous_time_s is None
            or time_s <= self.previous_time_s
            or time_s - self.previous_time_s > self.rules.maximum_sample_gap_s
        ):
            self._reset(time_s, pressure_mpa)
            return
        self.previous_time_s = time_s
        assert self.peak_time_s is not None
        assert self.peak_pressure_mpa is not None
        if not self.falling:
            if pressure_mpa >= self.peak_pressure_mpa:
                self.peak_pressure_mpa = pressure_mpa
                self.peak_time_s = time_s
                return
            if self.peak_pressure_mpa - pressure_mpa >= self.rules.fall_confirmation_mpa:
                self.falling = True
                self.trough_pressure_mpa = pressure_mpa
                self.trough_time_s = time_s
            return

        assert self.trough_time_s is not None
        assert self.trough_pressure_mpa is not None
        if pressure_mpa < self.trough_pressure_mpa:
            self.trough_pressure_mpa = pressure_mpa
            self.trough_time_s = time_s
            return
        if pressure_mpa - self.trough_pressure_mpa < self.rules.rise_confirmation_mpa:
            return
        cycle = PressureCycle(
            peak_time_s=self.peak_time_s,
            trough_time_s=self.trough_time_s,
            peak_pressure_mpa=self.peak_pressure_mpa,
            trough_pressure_mpa=self.trough_pressure_mpa,
        )
        if (
            self.rules.minimum_cycle_drop_mpa
            <= cycle.pressure_drop_mpa
            <= self.rules.maximum_cycle_drop_mpa
            and self.rules.minimum_decline_duration_s
            <= cycle.decline_duration_s
            <= self.rules.maximum_decline_duration_s
        ):
            self.cycles.append(cycle)
        self._reset(time_s, pressure_mpa)


def detect_pressure_cycles(
    samples: list[tuple[float, float]],
    *,
    rules: PressureCycleRules | None = None,
) -> list[PressureCycle]:
    detector = _CycleDetector(rules or PressureCycleRules())
    for time_s, pressure_mpa in samples:
        detector.add(float(time_s), float(pressure_mpa))
    return detector.cycles


def _stats(values: list[float]) -> dict[str, float | int | None]:
    ordered = sorted(value for value in values if math.isfinite(value))
    return {
        "count": len(ordered),
        "p10": round(_quantile(ordered, 0.10), 6) if ordered else None,
        "median": round(median(ordered), 6) if ordered else None,
        "p90": round(_quantile(ordered, 0.90), 6) if ordered else None,
    }


def _pressure_schema(mapping: Mapping[str, object]) -> Mapping[str, object]:
    schemas = mapping.get("schemas")
    if not isinstance(schemas, list):
        raise ValueError("mapping must contain schemas")
    for schema in schemas:
        if isinstance(schema, Mapping) and schema.get("schema_id") == "pressure_flow_candidate":
            return schema
    raise ValueError("pressure_flow_candidate schema is required")


def evaluate_confidential_pressure_cycle_holdout(
    input_path: Path,
    mapping: Mapping[str, object],
    *,
    rules: PressureCycleRules | None = None,
    role: str = "high_storage_pressure",
    frozen_candidate_mpa: float = 4.5,
) -> dict[str, object]:
    """Evaluate a predeclared pressure-cycle candidate without exporting source data."""

    selected_rules = rules or PressureCycleRules()
    attestation = mapping.get("attestation")
    if not isinstance(attestation, Mapping) or (
        attestation.get("medium_high_pressure_roles_attested_elsewhere") is not True
    ):
        raise ValueError("owner attestation for medium/high pressure roles is required")
    schema = _pressure_schema(mapping)
    channels = schema.get("numeric_channels")
    if not isinstance(channels, list):
        raise ValueError("pressure schema numeric channels are required")
    role_indices = {
        str(item.get("role")): int(item.get("index"))
        for item in channels
        if isinstance(item, Mapping) and item.get("role") is not None
    }
    if role not in role_indices:
        raise ValueError("requested pressure role is not mapped")
    expected_fingerprint = str(schema.get("header_fingerprint") or "")
    timestamp_index = int(schema.get("timestamp_index", 0))
    skip_rows = int(schema.get("skip_rows_after_header", 1))
    role_index = role_indices[role]

    files_read = 0
    raw_rows = 0
    sampled_rows = 0
    rejected_samples = 0
    calibration_cycles: list[PressureCycle] = []
    holdout_cycles: list[PressureCycle] = []
    calibration_files = 0
    holdout_files = 0

    for path in sorted(Path(input_path).rglob("*.csv")):
        header_record = _read_header(path)
        if header_record is None:
            continue
        encoding, delimiter, header = header_record
        if header_fingerprint(header) != expected_fingerprint:
            continue
        files_read += 1
        samples: list[tuple[float, float]] = []
        with path.open("r", encoding=encoding, newline="") as handle:
            handle.readline()
            for _ in range(skip_rows):
                handle.readline()
            for row_number, line in enumerate(handle):
                raw_rows += 1
                if row_number % selected_rules.sample_stride:
                    continue
                try:
                    row = next(csv.reader([line], delimiter=delimiter))
                except csv.Error:
                    rejected_samples += 1
                    continue
                if max(timestamp_index, role_index) >= len(row):
                    rejected_samples += 1
                    continue
                timestamp = _parse_time(row[timestamp_index])
                try:
                    pressure = float(row[role_index])
                except (TypeError, ValueError):
                    pressure = float("nan")
                if timestamp is None or not math.isfinite(pressure):
                    rejected_samples += 1
                    continue
                samples.append((float(timestamp), pressure))
                sampled_rows += 1
        if len(samples) < 2:
            continue
        cycles = detect_pressure_cycles(samples, rules=selected_rules)
        start_time, end_time = samples[0][0], samples[-1][0]
        split_time = start_time + selected_rules.calibration_fraction * (end_time - start_time)
        before = [cycle for cycle in cycles if cycle.trough_time_s < split_time]
        after = [cycle for cycle in cycles if cycle.trough_time_s >= split_time]
        calibration_cycles.extend(before)
        holdout_cycles.extend(after)
        calibration_files += int(bool(before))
        holdout_files += int(bool(after))

    calibration = _stats([cycle.pressure_drop_mpa for cycle in calibration_cycles])
    holdout = _stats([cycle.pressure_drop_mpa for cycle in holdout_cycles])
    holdout_median = holdout["median"]
    calibration_median = calibration["median"]
    candidate_inside_holdout_p10_p90 = bool(
        isinstance(holdout["p10"], (int, float))
        and isinstance(holdout["p90"], (int, float))
        and holdout["p10"] <= frozen_candidate_mpa <= holdout["p90"]
    )
    candidate_relative_median_error_percent = (
        round(abs(frozen_candidate_mpa - holdout_median) / holdout_median * 100.0, 6)
        if isinstance(holdout_median, (int, float)) and holdout_median > 0.0
        else None
    )
    temporal_median_shift_percent = (
        round(abs(holdout_median - calibration_median) / calibration_median * 100.0, 6)
        if isinstance(holdout_median, (int, float))
        and isinstance(calibration_median, (int, float))
        and calibration_median > 0.0
        else None
    )
    eligibility = {
        "minimum_files_met": files_read >= 6,
        "minimum_calibration_cycles_met": len(calibration_cycles) >= 30,
        "minimum_holdout_cycles_met": len(holdout_cycles) >= 15,
        "minimum_holdout_files_met": holdout_files >= 4,
    }
    screens = {
        "candidate_inside_holdout_p10_p90": candidate_inside_holdout_p10_p90,
        "candidate_relative_median_error_le_20_percent": bool(
            candidate_relative_median_error_percent is not None
            and candidate_relative_median_error_percent <= 20.0
        ),
        "calibration_holdout_median_shift_le_25_percent": bool(
            temporal_median_shift_percent is not None
            and temporal_median_shift_percent <= 25.0
        ),
    }
    supported = all(eligibility.values()) and all(screens.values())
    return {
        "schema_version": 1,
        "artifact_type": "confidential_station_pressure_cycle_holdout",
        "source_identifiers_published": False,
        "source_paths_published": False,
        "source_filenames_published": False,
        "source_headers_published": False,
        "raw_rows_persisted": False,
        "absolute_timestamps_published": False,
        "calendar_dates_published": False,
        "role": role,
        "frozen_candidate_mpa": frozen_candidate_mpa,
        "files_read": files_read,
        "raw_data_rows": raw_rows,
        "sampled_rows": sampled_rows,
        "rejected_sample_rows": rejected_samples,
        "rules": {
            key: getattr(selected_rules, key)
            for key in selected_rules.__dataclass_fields__
        },
        "calibration": {"files_with_cycles": calibration_files, "pressure_drop_mpa": calibration},
        "holdout": {"files_with_cycles": holdout_files, "pressure_drop_mpa": holdout},
        "metrics": {
            "candidate_relative_holdout_median_error_percent": candidate_relative_median_error_percent,
            "calibration_holdout_median_shift_percent": temporal_median_shift_percent,
        },
        "eligibility": eligibility,
        "screens": screens,
        "decision": {
            "existing_high_bank_restart_margin_cross_format_corroborated": supported,
            "runtime_parameter_application": False,
            "default_model_parameters_changed": False,
            "full_loop_holdout_eligible": False,
        },
        "claim_boundary": (
            "Same-site, cross-format station-side pressure-cycle corroboration only. "
            "It does not identify compressor state, validate vehicle filling, establish "
            "a safety limit, estimate accident frequency or certify field operation."
        ),
    }


__all__ = [
    "PressureCycle",
    "PressureCycleRules",
    "detect_pressure_cycles",
    "evaluate_confidential_pressure_cycle_holdout",
]
