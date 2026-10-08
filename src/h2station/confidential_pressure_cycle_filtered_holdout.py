"""Versioned causal-filter revision of the confidential pressure-cycle holdout.

The first frozen detector is preserved unchanged.  This revision adds one
predeclared seven-sample causal median filter after the first result showed that
local reversals interrupted every unsmoothed cycle.  It remains same-site
method-revision evidence rather than an independent external validation.
"""

from __future__ import annotations

from collections import deque
import csv
import math
from pathlib import Path
from statistics import median
from typing import Mapping

from .confidential_history_profile import _read_header, header_fingerprint
from .confidential_pressure_cycle_holdout import (
    PressureCycle,
    PressureCycleRules,
    _pressure_schema,
    _stats,
    detect_pressure_cycles,
)
from .confidential_signal_consistency import _parse_time


def causal_median_filter(
    samples: list[tuple[float, float]],
    *,
    window_samples: int,
) -> list[tuple[float, float]]:
    if window_samples < 3 or window_samples % 2 == 0:
        raise ValueError("causal median window must be an odd integer of at least three")
    window: deque[float] = deque(maxlen=window_samples)
    filtered: list[tuple[float, float]] = []
    for time_s, value in samples:
        window.append(float(value))
        if len(window) == window_samples:
            filtered.append((float(time_s), float(median(window))))
    return filtered


def _mapped_role(mapping: Mapping[str, object], role: str) -> tuple[Mapping[str, object], int]:
    attestation = mapping.get("attestation")
    if not isinstance(attestation, Mapping) or (
        attestation.get("medium_high_pressure_roles_attested_elsewhere") is not True
    ):
        raise ValueError("owner attestation for medium/high pressure roles is required")
    schema = _pressure_schema(mapping)
    channels = schema.get("numeric_channels")
    if not isinstance(channels, list):
        raise ValueError("pressure schema numeric channels are required")
    roles = {
        str(item.get("role")): int(item.get("index"))
        for item in channels
        if isinstance(item, Mapping) and item.get("role") is not None
    }
    if role not in roles:
        raise ValueError("requested pressure role is not mapped")
    return schema, roles[role]


def _split_cycles(
    cycles: list[PressureCycle],
    samples: list[tuple[float, float]],
    calibration_fraction: float,
) -> tuple[list[PressureCycle], list[PressureCycle]]:
    start_time, end_time = samples[0][0], samples[-1][0]
    split_time = start_time + calibration_fraction * (end_time - start_time)
    return (
        [cycle for cycle in cycles if cycle.trough_time_s < split_time],
        [cycle for cycle in cycles if cycle.trough_time_s >= split_time],
    )


def evaluate_filtered_pressure_cycle_holdout(
    input_path: Path,
    mapping: Mapping[str, object],
    *,
    rules: PressureCycleRules | None = None,
    role: str = "high_storage_pressure",
    frozen_candidate_mpa: float = 4.5,
    median_window_samples: int = 7,
) -> dict[str, object]:
    selected_rules = rules or PressureCycleRules()
    if median_window_samples < 3 or median_window_samples % 2 == 0:
        raise ValueError("median_window_samples must be an odd integer of at least three")
    schema, role_index = _mapped_role(mapping, role)
    expected_fingerprint = str(schema.get("header_fingerprint") or "")
    timestamp_index = int(schema.get("timestamp_index", 0))
    skip_rows = int(schema.get("skip_rows_after_header", 1))

    files_read = raw_rows = sampled_rows = filtered_rows = rejected_samples = 0
    calibration_files = holdout_files = 0
    calibration_cycles: list[PressureCycle] = []
    holdout_cycles: list[PressureCycle] = []
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
        filtered = causal_median_filter(samples, window_samples=median_window_samples)
        filtered_rows += len(filtered)
        if len(filtered) < 2:
            continue
        before, after = _split_cycles(
            detect_pressure_cycles(filtered, rules=selected_rules),
            filtered,
            selected_rules.calibration_fraction,
        )
        calibration_cycles.extend(before)
        holdout_cycles.extend(after)
        calibration_files += int(bool(before))
        holdout_files += int(bool(after))

    calibration = _stats([cycle.pressure_drop_mpa for cycle in calibration_cycles])
    holdout = _stats([cycle.pressure_drop_mpa for cycle in holdout_cycles])
    holdout_median = holdout["median"]
    calibration_median = calibration["median"]
    candidate_inside = bool(
        isinstance(holdout["p10"], (int, float))
        and isinstance(holdout["p90"], (int, float))
        and holdout["p10"] <= frozen_candidate_mpa <= holdout["p90"]
    )
    candidate_error = (
        round(abs(frozen_candidate_mpa - holdout_median) / holdout_median * 100.0, 6)
        if isinstance(holdout_median, (int, float)) and holdout_median > 0.0
        else None
    )
    median_shift = (
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
        "candidate_inside_holdout_p10_p90": candidate_inside,
        "candidate_relative_median_error_le_20_percent": bool(
            candidate_error is not None and candidate_error <= 20.0
        ),
        "calibration_holdout_median_shift_le_25_percent": bool(
            median_shift is not None and median_shift <= 25.0
        ),
    }
    supported = all(eligibility.values()) and all(screens.values())
    return {
        "schema_version": 1,
        "artifact_type": "confidential_station_filtered_pressure_cycle_holdout",
        "evidence_role": "disclosed_sequential_method_revision_holdout",
        "prior_unsmoothed_failure_known": True,
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
        "filtered_rows": filtered_rows,
        "rejected_sample_rows": rejected_samples,
        "filter": {
            "kind": "causal_rolling_median",
            "window_samples": median_window_samples,
            "nominal_window_seconds": median_window_samples * selected_rules.sample_stride,
        },
        "rules": {
            key: getattr(selected_rules, key)
            for key in selected_rules.__dataclass_fields__
        },
        "calibration": {"files_with_cycles": calibration_files, "pressure_drop_mpa": calibration},
        "holdout": {"files_with_cycles": holdout_files, "pressure_drop_mpa": holdout},
        "metrics": {
            "candidate_relative_holdout_median_error_percent": candidate_error,
            "calibration_holdout_median_shift_percent": median_shift,
        },
        "eligibility": eligibility,
        "screens": screens,
        "decision": {
            "existing_high_bank_restart_margin_cross_format_corroborated": supported,
            "independent_external_validation": False,
            "runtime_parameter_application": False,
            "default_model_parameters_changed": False,
            "full_loop_holdout_eligible": False,
        },
        "claim_boundary": (
            "Sequential same-site method-revision evidence only. The prior unsmoothed "
            "failure was known before this filter was frozen. This result does not "
            "identify compressor state, validate vehicle filling, establish a safety "
            "limit, estimate accident frequency or certify field operation."
        ),
    }


__all__ = ["causal_median_filter", "evaluate_filtered_pressure_cycle_holdout"]
