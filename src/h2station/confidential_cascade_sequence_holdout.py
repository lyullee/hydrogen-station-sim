"""Privacy-bounded medium-to-high cascade sequence holdout.

The owner-attested pressure roles are evaluated in memory.  Source names,
headers, timestamps and rows never enter the returned publication surface.
"""

from __future__ import annotations

from dataclasses import dataclass
import csv
import math
from pathlib import Path
from typing import Mapping

from .confidential_history_profile import _read_header, header_fingerprint
from .confidential_pressure_cycle_filtered_holdout import causal_median_filter
from .confidential_pressure_cycle_holdout import (
    PressureCycle,
    PressureCycleRules,
    _pressure_schema,
    _stats,
    detect_pressure_cycles,
)
from .confidential_signal_consistency import _parse_time


@dataclass(frozen=True, slots=True)
class CascadeSequenceRules:
    median_window_samples: int = 7
    minimum_pair_gap_s: float = -300.0
    maximum_pair_gap_s: float = 900.0
    minimum_matching_files: int = 6
    minimum_calibration_pairs: int = 60
    minimum_holdout_pairs: int = 24
    minimum_holdout_files: int = 4
    minimum_holdout_pair_coverage: float = 0.60
    minimum_holdout_sequential_fraction: float = 0.90
    maximum_sequential_fraction_shift: float = 0.10
    maximum_pair_coverage_shift: float = 0.20

    def __post_init__(self) -> None:
        if self.median_window_samples < 3 or self.median_window_samples % 2 == 0:
            raise ValueError("median window must be an odd integer of at least three")
        if self.maximum_pair_gap_s <= self.minimum_pair_gap_s:
            raise ValueError("maximum pair gap must exceed minimum pair gap")
        if min(
            self.minimum_matching_files,
            self.minimum_calibration_pairs,
            self.minimum_holdout_pairs,
            self.minimum_holdout_files,
        ) <= 0:
            raise ValueError("count thresholds must be positive")
        fractions = (
            self.minimum_holdout_pair_coverage,
            self.minimum_holdout_sequential_fraction,
            self.maximum_sequential_fraction_shift,
            self.maximum_pair_coverage_shift,
        )
        if any(not 0.0 <= value <= 1.0 for value in fractions):
            raise ValueError("fraction thresholds must be in [0, 1]")


@dataclass(frozen=True, slots=True)
class CascadeSequencePair:
    medium: PressureCycle
    high: PressureCycle

    @property
    def handoff_gap_s(self) -> float:
        return self.high.peak_time_s - self.medium.trough_time_s

    @property
    def sequential(self) -> bool:
        return (
            self.medium.peak_time_s <= self.high.peak_time_s
            and self.medium.trough_time_s <= self.high.trough_time_s
        )


def pair_cascade_cycles(
    medium_cycles: list[PressureCycle],
    high_cycles: list[PressureCycle],
    *,
    minimum_pair_gap_s: float,
    maximum_pair_gap_s: float,
) -> list[CascadeSequencePair]:
    """Greedily pair each high-bank drawdown to the nearest unused medium event."""

    unused = set(range(len(medium_cycles)))
    pairs: list[CascadeSequencePair] = []
    for high in sorted(high_cycles, key=lambda cycle: cycle.peak_time_s):
        candidates: list[tuple[float, int, PressureCycle]] = []
        for index in unused:
            medium = medium_cycles[index]
            if medium.peak_time_s > high.peak_time_s:
                continue
            gap = high.peak_time_s - medium.trough_time_s
            if minimum_pair_gap_s <= gap <= maximum_pair_gap_s:
                candidates.append((abs(gap), index, medium))
        if not candidates:
            continue
        _distance, index, medium = min(
            candidates,
            key=lambda item: (item[0], -item[2].trough_time_s),
        )
        unused.remove(index)
        pairs.append(CascadeSequencePair(medium=medium, high=high))
    return pairs


def _fraction(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 6) if denominator else None


def _partition_summary(
    pairs: list[CascadeSequencePair],
    high_cycle_count: int,
    files_with_pairs: int,
) -> dict[str, object]:
    sequential_count = sum(pair.sequential for pair in pairs)
    return {
        "files_with_pairs": files_with_pairs,
        "high_cycle_count": high_cycle_count,
        "paired_episode_count": len(pairs),
        "pair_coverage_fraction": _fraction(len(pairs), high_cycle_count),
        "sequential_episode_count": sequential_count,
        "sequential_fraction": _fraction(sequential_count, len(pairs)),
        "handoff_gap_s": _stats([pair.handoff_gap_s for pair in pairs]),
        "medium_pressure_drop_mpa": _stats(
            [pair.medium.pressure_drop_mpa for pair in pairs]
        ),
        "high_pressure_drop_mpa": _stats(
            [pair.high.pressure_drop_mpa for pair in pairs]
        ),
    }


def evaluate_confidential_cascade_sequence_holdout(
    input_path: Path,
    mapping: Mapping[str, object],
    *,
    cycle_rules: PressureCycleRules | None = None,
    sequence_rules: CascadeSequenceRules | None = None,
) -> dict[str, object]:
    """Evaluate chronological medium/high drawdown ordering without source identity."""

    cycles = cycle_rules or PressureCycleRules()
    sequence = sequence_rules or CascadeSequenceRules()
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
    required_roles = ("medium_storage_pressure", "high_storage_pressure")
    if any(role not in role_indices for role in required_roles):
        raise ValueError("mapped medium and high storage pressure roles are required")
    expected_fingerprint = str(schema.get("header_fingerprint") or "")
    timestamp_index = int(schema.get("timestamp_index", 0))
    skip_rows = int(schema.get("skip_rows_after_header", 1))
    medium_index = role_indices[required_roles[0]]
    high_index = role_indices[required_roles[1]]

    files_read = reverse_files = mixed_files = 0
    raw_rows = sampled_rows = filtered_rows = rejected_rows = 0
    calibration_pairs: list[CascadeSequencePair] = []
    holdout_pairs: list[CascadeSequencePair] = []
    calibration_high_count = holdout_high_count = 0
    calibration_files = holdout_files = 0

    for path in sorted(Path(input_path).rglob("*.csv")):
        header_record = _read_header(path)
        if header_record is None:
            continue
        encoding, delimiter, header = header_record
        if header_fingerprint(header) != expected_fingerprint:
            continue
        files_read += 1
        samples: list[tuple[float, float, float, int]] = []
        with path.open("r", encoding=encoding, newline="") as handle:
            handle.readline()
            for _ in range(skip_rows):
                handle.readline()
            for row_number, line in enumerate(handle):
                raw_rows += 1
                if row_number % cycles.sample_stride:
                    continue
                try:
                    row = next(csv.reader([line], delimiter=delimiter))
                except csv.Error:
                    rejected_rows += 1
                    continue
                if max(timestamp_index, medium_index, high_index) >= len(row):
                    rejected_rows += 1
                    continue
                timestamp = _parse_time(row[timestamp_index])
                try:
                    medium_pressure = float(row[medium_index])
                    high_pressure = float(row[high_index])
                except (TypeError, ValueError):
                    medium_pressure = high_pressure = float("nan")
                if (
                    timestamp is None
                    or not math.isfinite(medium_pressure)
                    or not math.isfinite(high_pressure)
                ):
                    rejected_rows += 1
                    continue
                samples.append(
                    (float(timestamp), medium_pressure, high_pressure, row_number)
                )
                sampled_rows += 1
        if len(samples) < 2:
            continue
        increasing = sum(after[0] > before[0] for before, after in zip(samples, samples[1:]))
        decreasing = sum(after[0] < before[0] for before, after in zip(samples, samples[1:]))
        reverse_files += int(decreasing > 0 and increasing == 0)
        mixed_files += int(decreasing > 0 and increasing > 0)
        samples.sort(key=lambda item: (item[0], item[3]))
        chronological: list[tuple[float, float, float]] = []
        for time_s, medium_pressure, high_pressure, _source_order in samples:
            item = (time_s, medium_pressure, high_pressure)
            if chronological and time_s == chronological[-1][0]:
                chronological[-1] = item
            else:
                chronological.append(item)
        medium_filtered = causal_median_filter(
            [(item[0], item[1]) for item in chronological],
            window_samples=sequence.median_window_samples,
        )
        high_filtered = causal_median_filter(
            [(item[0], item[2]) for item in chronological],
            window_samples=sequence.median_window_samples,
        )
        filtered_rows += min(len(medium_filtered), len(high_filtered))
        if len(medium_filtered) < 2 or len(high_filtered) < 2:
            continue
        start_time = max(medium_filtered[0][0], high_filtered[0][0])
        end_time = min(medium_filtered[-1][0], high_filtered[-1][0])
        split_time = start_time + cycles.calibration_fraction * (end_time - start_time)
        medium_detected = detect_pressure_cycles(medium_filtered, rules=cycles)
        high_detected = detect_pressure_cycles(high_filtered, rules=cycles)
        medium_before = [item for item in medium_detected if item.trough_time_s < split_time]
        medium_after = [item for item in medium_detected if item.trough_time_s >= split_time]
        high_before = [item for item in high_detected if item.trough_time_s < split_time]
        high_after = [item for item in high_detected if item.trough_time_s >= split_time]
        before_pairs = pair_cascade_cycles(
            medium_before,
            high_before,
            minimum_pair_gap_s=sequence.minimum_pair_gap_s,
            maximum_pair_gap_s=sequence.maximum_pair_gap_s,
        )
        after_pairs = pair_cascade_cycles(
            medium_after,
            high_after,
            minimum_pair_gap_s=sequence.minimum_pair_gap_s,
            maximum_pair_gap_s=sequence.maximum_pair_gap_s,
        )
        calibration_pairs.extend(before_pairs)
        holdout_pairs.extend(after_pairs)
        calibration_high_count += len(high_before)
        holdout_high_count += len(high_after)
        calibration_files += int(bool(before_pairs))
        holdout_files += int(bool(after_pairs))

    calibration = _partition_summary(
        calibration_pairs, calibration_high_count, calibration_files
    )
    holdout = _partition_summary(holdout_pairs, holdout_high_count, holdout_files)
    calibration_pair_coverage = calibration["pair_coverage_fraction"]
    holdout_pair_coverage = holdout["pair_coverage_fraction"]
    calibration_sequential = calibration["sequential_fraction"]
    holdout_sequential = holdout["sequential_fraction"]
    calibration_gap = calibration["handoff_gap_s"]
    holdout_gap = holdout["handoff_gap_s"]
    coverage_shift = (
        round(abs(holdout_pair_coverage - calibration_pair_coverage), 6)
        if isinstance(holdout_pair_coverage, float)
        and isinstance(calibration_pair_coverage, float)
        else None
    )
    sequential_shift = (
        round(abs(holdout_sequential - calibration_sequential), 6)
        if isinstance(holdout_sequential, float)
        and isinstance(calibration_sequential, float)
        else None
    )
    median_gap_stable = bool(
        isinstance(calibration_gap.get("p10"), (int, float))
        and isinstance(calibration_gap.get("p90"), (int, float))
        and isinstance(holdout_gap.get("median"), (int, float))
        and calibration_gap["p10"]
        <= holdout_gap["median"]
        <= calibration_gap["p90"]
    )
    eligibility = {
        "minimum_files_met": files_read >= sequence.minimum_matching_files,
        "all_files_have_deterministic_time_order": mixed_files == 0,
        "minimum_calibration_pairs_met": (
            len(calibration_pairs) >= sequence.minimum_calibration_pairs
        ),
        "minimum_holdout_pairs_met": len(holdout_pairs) >= sequence.minimum_holdout_pairs,
        "minimum_holdout_files_met": holdout_files >= sequence.minimum_holdout_files,
    }
    screens = {
        "holdout_pair_coverage_met": bool(
            isinstance(holdout_pair_coverage, float)
            and holdout_pair_coverage >= sequence.minimum_holdout_pair_coverage
        ),
        "holdout_sequential_fraction_met": bool(
            isinstance(holdout_sequential, float)
            and holdout_sequential >= sequence.minimum_holdout_sequential_fraction
        ),
        "sequential_fraction_shift_met": bool(
            sequential_shift is not None
            and sequential_shift <= sequence.maximum_sequential_fraction_shift
        ),
        "pair_coverage_shift_met": bool(
            coverage_shift is not None
            and coverage_shift <= sequence.maximum_pair_coverage_shift
        ),
        "holdout_median_gap_inside_calibration_p10_p90": median_gap_stable,
    }
    supported = all(eligibility.values()) and all(screens.values())
    return {
        "schema_version": 1,
        "artifact_type": "confidential_station_cascade_sequence_holdout",
        "evidence_role": "same_site_medium_high_pressure_sequence_holdout",
        "ordered_joint_outcomes_seen_before_freeze": False,
        "source_identifiers_published": False,
        "source_paths_published": False,
        "source_filenames_published": False,
        "source_headers_published": False,
        "raw_rows_persisted": False,
        "absolute_timestamps_published": False,
        "calendar_dates_published": False,
        "files_read": files_read,
        "reverse_chronological_files": reverse_files,
        "mixed_order_files": mixed_files,
        "raw_data_rows": raw_rows,
        "sampled_rows": sampled_rows,
        "filtered_rows": filtered_rows,
        "rejected_sample_rows": rejected_rows,
        "roles": list(required_roles),
        "cycle_rules": {
            key: getattr(cycles, key) for key in cycles.__dataclass_fields__
        },
        "sequence_rules": {
            key: getattr(sequence, key) for key in sequence.__dataclass_fields__
        },
        "calibration": calibration,
        "holdout": holdout,
        "metrics": {
            "pair_coverage_shift": coverage_shift,
            "sequential_fraction_shift": sequential_shift,
        },
        "eligibility": eligibility,
        "screens": screens,
        "decision": {
            "medium_to_high_drawdown_sequence_corroborated": supported,
            "cascade_controller_structure_supported": supported,
            "runtime_parameter_application": False,
            "default_model_parameters_changed": False,
            "vehicle_fill_validation": False,
            "full_loop_holdout_eligible": False,
            "independent_external_validation": False,
        },
        "claim_boundary": (
            "Same-site medium/high pressure sequence evidence only. Paired pressure "
            "drawdowns are compatible with, but do not uniquely prove, a vehicle-fill "
            "cascade handoff because vehicle, valve and dispenser states are absent. "
            "The result does not validate the low bank, a complete fill, a safety "
            "limit, accident frequency or field certification."
        ),
    }


__all__ = [
    "CascadeSequencePair",
    "CascadeSequenceRules",
    "evaluate_confidential_cascade_sequence_holdout",
    "pair_cascade_cycles",
]
