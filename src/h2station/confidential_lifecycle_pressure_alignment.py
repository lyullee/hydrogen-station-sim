"""Privacy-bounded storage recharge-counter and pressure-event alignment.

The evaluator joins owner-attested storage pressure completion events to
owner-attested full-recharge counter increments. Source paths, file names,
headers, absolute timestamps, and raw rows never enter the returned result.
"""

from __future__ import annotations

from bisect import bisect_left
from dataclasses import dataclass
import csv
import hashlib
import math
from pathlib import Path
from statistics import median
from typing import Mapping

from .confidential_history_profile import _read_header, header_fingerprint
from .confidential_signal_consistency import _parse_time
from .controlled_station_replay import _quantile


@dataclass(frozen=True, slots=True)
class LifecyclePressureAlignmentRules:
    calibration_fraction: float = 0.70
    medium_full_pressure_mpa: float = 45.0
    high_full_pressure_mpa: float = 85.0
    completion_threshold_fraction: float = 0.99
    rearm_drop_mpa: float = 0.50
    maximum_sample_gap_s: float = 2.5
    maximum_match_offset_s: float = 300.0
    minimum_pressure_mpa: float = 10.0
    maximum_pressure_mpa: float = 100.0
    minimum_pressure_files: int = 6
    minimum_counter_files: int = 6
    minimum_calibration_counter_events_per_bank: int = 200
    minimum_holdout_counter_events_per_bank: int = 50
    minimum_holdout_counter_recall: float = 0.80
    minimum_holdout_pressure_precision: float = 0.70
    maximum_recall_shift: float = 0.10
    maximum_holdout_median_absolute_offset_s: float = 120.0

    def __post_init__(self) -> None:
        if not 0.5 <= self.calibration_fraction < 1.0:
            raise ValueError("calibration_fraction must be in [0.5, 1.0)")
        positive = (
            self.medium_full_pressure_mpa,
            self.high_full_pressure_mpa,
            self.completion_threshold_fraction,
            self.rearm_drop_mpa,
            self.maximum_sample_gap_s,
            self.maximum_match_offset_s,
            self.minimum_pressure_mpa,
            self.maximum_pressure_mpa,
            self.minimum_pressure_files,
            self.minimum_counter_files,
            self.minimum_calibration_counter_events_per_bank,
            self.minimum_holdout_counter_events_per_bank,
            self.minimum_holdout_counter_recall,
            self.minimum_holdout_pressure_precision,
            self.maximum_recall_shift,
            self.maximum_holdout_median_absolute_offset_s,
        )
        if any(not math.isfinite(float(value)) or float(value) <= 0.0 for value in positive):
            raise ValueError("alignment rules must be positive and finite")
        if not 0.0 < self.completion_threshold_fraction <= 1.0:
            raise ValueError("completion threshold fraction must be in (0, 1]")
        if self.maximum_pressure_mpa <= self.minimum_pressure_mpa:
            raise ValueError("maximum pressure must exceed minimum pressure")
        for fraction in (
            self.minimum_holdout_counter_recall,
            self.minimum_holdout_pressure_precision,
            self.maximum_recall_shift,
        ):
            if not 0.0 <= fraction <= 1.0:
                raise ValueError("fraction rules must be in [0, 1]")


@dataclass(frozen=True, slots=True)
class CounterEvent:
    time_s: float
    increment: int


def _schema(mapping: Mapping[str, object], schema_id: str) -> Mapping[str, object]:
    schemas = mapping.get("schemas")
    if not isinstance(schemas, list):
        raise ValueError("mapping must contain schemas")
    for item in schemas:
        if isinstance(item, Mapping) and item.get("schema_id") == schema_id:
            return item
    raise ValueError(f"{schema_id} schema is required")


def _role_indices(schema: Mapping[str, object]) -> dict[str, int]:
    channels = schema.get("numeric_channels")
    if not isinstance(channels, list):
        raise ValueError("schema numeric_channels are required")
    return {
        str(item.get("role")): int(item.get("index"))
        for item in channels
        if isinstance(item, Mapping) and item.get("role") is not None
    }


def _finite(value: object) -> float | None:
    try:
        parsed = float(str(value).strip())
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(8 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _stats(values: list[float]) -> dict[str, int | float | None]:
    ordered = sorted(value for value in values if math.isfinite(value))
    return {
        "count": len(ordered),
        "p10": round(_quantile(ordered, 0.10), 6) if ordered else None,
        "median": round(median(ordered), 6) if ordered else None,
        "p90": round(_quantile(ordered, 0.90), 6) if ordered else None,
    }


def _fraction(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 6) if denominator else None


def _pressure_events_reverse(
    rows: list[tuple[float, float]],
    *,
    completion_threshold_mpa: float,
    rearm_threshold_mpa: float,
    maximum_sample_gap_s: float,
) -> list[float]:
    """Detect chronological upward completions from newest-to-oldest samples."""

    events: list[float] = []
    candidate_time: float | None = None
    previous_time: float | None = None
    for time_s, pressure_mpa in rows:
        if previous_time is not None and (
            time_s >= previous_time or previous_time - time_s > maximum_sample_gap_s
        ):
            candidate_time = None
        previous_time = time_s
        if pressure_mpa >= completion_threshold_mpa:
            candidate_time = time_s
        elif candidate_time is not None and pressure_mpa <= rearm_threshold_mpa:
            events.append(candidate_time)
            candidate_time = None
    events.sort()
    return events


def _match_events(
    pressure_events: list[float],
    counter_events: list[CounterEvent],
    *,
    maximum_offset_s: float,
) -> tuple[list[float], int]:
    available = list(sorted(pressure_events))
    offsets: list[float] = []
    matched_counter_increment = 0
    for event in sorted(counter_events, key=lambda item: item.time_s):
        if not available:
            break
        position = bisect_left(available, event.time_s)
        candidates = []
        if position < len(available):
            candidates.append((abs(available[position] - event.time_s), position))
        if position:
            candidates.append((abs(available[position - 1] - event.time_s), position - 1))
        if not candidates:
            continue
        distance, index = min(candidates)
        if distance > maximum_offset_s:
            continue
        pressure_time = available.pop(index)
        offsets.append(pressure_time - event.time_s)
        matched_counter_increment += event.increment
    return offsets, matched_counter_increment


def _partition_summary(
    pressure_by_bank: Mapping[str, list[float]],
    counter_by_bank: Mapping[str, list[CounterEvent]],
    *,
    maximum_offset_s: float,
) -> dict[str, object]:
    by_bank: dict[str, object] = {}
    combined_pressure = combined_counter = combined_matches = 0
    combined_offsets: list[float] = []
    for bank in ("medium", "high"):
        pressure = list(pressure_by_bank.get(bank, []))
        counter = list(counter_by_bank.get(bank, []))
        offsets, matched_increment = _match_events(
            pressure, counter, maximum_offset_s=maximum_offset_s
        )
        counter_increment_total = sum(item.increment for item in counter)
        summary = {
            "pressure_completion_event_count": len(pressure),
            "counter_increment_event_count": len(counter),
            "counter_increment_total": counter_increment_total,
            "matched_event_count": len(offsets),
            "matched_counter_increment_total": matched_increment,
            "counter_event_recall": _fraction(len(offsets), len(counter)),
            "pressure_event_precision": _fraction(len(offsets), len(pressure)),
            "time_offset_s": _stats(offsets),
            "absolute_time_offset_s": _stats([abs(value) for value in offsets]),
        }
        by_bank[bank] = summary
        combined_pressure += len(pressure)
        combined_counter += len(counter)
        combined_matches += len(offsets)
        combined_offsets.extend(offsets)
    return {
        "by_bank": by_bank,
        "combined": {
            "pressure_completion_event_count": combined_pressure,
            "counter_increment_event_count": combined_counter,
            "matched_event_count": combined_matches,
            "counter_event_recall": _fraction(combined_matches, combined_counter),
            "pressure_event_precision": _fraction(combined_matches, combined_pressure),
            "time_offset_s": _stats(combined_offsets),
            "absolute_time_offset_s": _stats([abs(value) for value in combined_offsets]),
        },
    }


def evaluate_lifecycle_pressure_alignment(
    input_path: Path,
    mapping: Mapping[str, object],
    *,
    rules: LifecyclePressureAlignmentRules | None = None,
) -> dict[str, object]:
    selected = rules or LifecyclePressureAlignmentRules()
    attestation = mapping.get("attestation")
    if not isinstance(attestation, Mapping):
        raise ValueError("mapping attestation is required")
    required_attestations = (
        "medium_high_pressure_roles_attested_elsewhere",
        "lifecycle_counter_roles_attested_elsewhere",
        "full_recharge_thresholds_attested",
        "local_clock_alignment_attested",
    )
    if any(attestation.get(key) is not True for key in required_attestations):
        raise ValueError("pressure, counter, threshold and clock attestations are required")

    pressure_schema = _schema(mapping, "pressure_flow_candidate")
    counter_schema = _schema(mapping, "lifecycle_counter_candidate")
    pressure_roles = _role_indices(pressure_schema)
    counter_roles = _role_indices(counter_schema)
    required_pressure = {
        "medium_storage_pressure": "medium",
        "high_storage_pressure": "high",
    }
    required_counter = {
        "medium_bank_full_recharge_counter": "medium",
        "high_bank_full_recharge_counter": "high",
    }
    if any(role not in pressure_roles for role in required_pressure):
        raise ValueError("mapped medium and high pressure roles are required")
    if any(role not in counter_roles for role in required_counter):
        raise ValueError("mapped medium and high lifecycle counters are required")

    pressure_fingerprint = str(pressure_schema.get("header_fingerprint") or "")
    counter_fingerprint = str(counter_schema.get("header_fingerprint") or "")
    pressure_time_index = int(pressure_schema.get("timestamp_index", 0))
    counter_time_index = int(counter_schema.get("timestamp_index", 0))
    pressure_skip = int(pressure_schema.get("skip_rows_after_header", 0))
    counter_skip = int(counter_schema.get("skip_rows_after_header", 0))
    pressure_files = counter_files = duplicate_files = 0
    raw_pressure_rows = raw_counter_rows = rejected_rows = 0
    pressure_events: dict[str, list[float]] = {"medium": [], "high": []}
    counter_events: dict[str, list[CounterEvent]] = {"medium": [], "high": []}
    sample_times: list[float] = []
    negative_counter_steps = 0
    seen_hashes: set[str] = set()

    for path in sorted(Path(input_path).rglob("*.csv")):
        header_record = _read_header(path)
        if header_record is None:
            continue
        encoding, delimiter, header = header_record
        fingerprint = header_fingerprint(header)
        if fingerprint not in {pressure_fingerprint, counter_fingerprint}:
            continue
        digest = _file_sha256(path)
        if digest in seen_hashes:
            duplicate_files += 1
            continue
        seen_hashes.add(digest)

        if fingerprint == pressure_fingerprint:
            pressure_files += 1
            samples: dict[str, list[tuple[float, float]]] = {
                "medium": [],
                "high": [],
            }
            with path.open("r", encoding=encoding, newline="") as stream:
                stream.readline()
                for _ in range(pressure_skip):
                    stream.readline()
                for line in stream:
                    raw_pressure_rows += 1
                    try:
                        row = next(csv.reader([line], delimiter=delimiter))
                    except csv.Error:
                        rejected_rows += 1
                        continue
                    maximum_index = max(
                        pressure_time_index,
                        *(pressure_roles[role] for role in required_pressure),
                    )
                    if maximum_index >= len(row):
                        rejected_rows += 1
                        continue
                    time_s = _parse_time(row[pressure_time_index])
                    values = {
                        bank: _finite(row[pressure_roles[role]])
                        for role, bank in required_pressure.items()
                    }
                    if time_s is None or any(value is None for value in values.values()):
                        rejected_rows += 1
                        continue
                    sample_times.append(float(time_s))
                    for bank, value in values.items():
                        assert value is not None
                        if selected.minimum_pressure_mpa <= value <= selected.maximum_pressure_mpa:
                            samples[bank].append((float(time_s), value))
            thresholds = {
                "medium": selected.medium_full_pressure_mpa,
                "high": selected.high_full_pressure_mpa,
            }
            for bank, full_pressure in thresholds.items():
                completion = full_pressure * selected.completion_threshold_fraction
                pressure_events[bank].extend(
                    _pressure_events_reverse(
                        samples[bank],
                        completion_threshold_mpa=completion,
                        rearm_threshold_mpa=completion - selected.rearm_drop_mpa,
                        maximum_sample_gap_s=selected.maximum_sample_gap_s,
                    )
                )
        else:
            counter_files += 1
            previous: dict[str, tuple[float, float] | None] = {
                "medium": None,
                "high": None,
            }
            with path.open("r", encoding=encoding, newline="") as stream:
                stream.readline()
                for _ in range(counter_skip):
                    stream.readline()
                for line in stream:
                    raw_counter_rows += 1
                    try:
                        row = next(csv.reader([line], delimiter=delimiter))
                    except csv.Error:
                        rejected_rows += 1
                        continue
                    maximum_index = max(
                        counter_time_index,
                        *(counter_roles[role] for role in required_counter),
                    )
                    if maximum_index >= len(row):
                        rejected_rows += 1
                        continue
                    time_s = _parse_time(row[counter_time_index])
                    values = {
                        bank: _finite(row[counter_roles[role]])
                        for role, bank in required_counter.items()
                    }
                    if time_s is None or any(value is None for value in values.values()):
                        rejected_rows += 1
                        continue
                    sample_times.append(float(time_s))
                    for bank, value in values.items():
                        assert value is not None
                        prior = previous[bank]
                        if prior is not None:
                            later_time, later_value = prior
                            if later_time > time_s:
                                delta = later_value - value
                                if delta > 0.0:
                                    rounded = int(round(delta))
                                    if rounded > 0 and abs(delta - rounded) <= 1.0e-6:
                                        counter_events[bank].append(
                                            CounterEvent(later_time, rounded)
                                        )
                                elif delta < 0.0:
                                    negative_counter_steps += 1
                        previous[bank] = (float(time_s), value)

    if not sample_times:
        raise ValueError("no mapped station samples were found")
    split_time = min(sample_times) + selected.calibration_fraction * (
        max(sample_times) - min(sample_times)
    )
    pressure_partitions = {
        "calibration": {
            bank: sorted({time for time in times if time < split_time})
            for bank, times in pressure_events.items()
        },
        "holdout": {
            bank: sorted({time for time in times if time >= split_time})
            for bank, times in pressure_events.items()
        },
    }
    counter_partitions = {
        "calibration": {
            bank: sorted(
                {event.time_s: event for event in events if event.time_s < split_time}.values(),
                key=lambda item: item.time_s,
            )
            for bank, events in counter_events.items()
        },
        "holdout": {
            bank: sorted(
                {event.time_s: event for event in events if event.time_s >= split_time}.values(),
                key=lambda item: item.time_s,
            )
            for bank, events in counter_events.items()
        },
    }
    calibration = _partition_summary(
        pressure_partitions["calibration"],
        counter_partitions["calibration"],
        maximum_offset_s=selected.maximum_match_offset_s,
    )
    holdout = _partition_summary(
        pressure_partitions["holdout"],
        counter_partitions["holdout"],
        maximum_offset_s=selected.maximum_match_offset_s,
    )
    recall_shift_by_bank: dict[str, float | None] = {}
    for bank in ("medium", "high"):
        cal = calibration["by_bank"][bank]["counter_event_recall"]
        test = holdout["by_bank"][bank]["counter_event_recall"]
        recall_shift_by_bank[bank] = (
            round(abs(test - cal), 6)
            if isinstance(cal, float) and isinstance(test, float)
            else None
        )
    eligibility = {
        "minimum_pressure_files_met": pressure_files >= selected.minimum_pressure_files,
        "minimum_counter_files_met": counter_files >= selected.minimum_counter_files,
        "minimum_calibration_counter_events_per_bank_met": all(
            calibration["by_bank"][bank]["counter_increment_event_count"]
            >= selected.minimum_calibration_counter_events_per_bank
            for bank in ("medium", "high")
        ),
        "minimum_holdout_counter_events_per_bank_met": all(
            holdout["by_bank"][bank]["counter_increment_event_count"]
            >= selected.minimum_holdout_counter_events_per_bank
            for bank in ("medium", "high")
        ),
        "counter_monotonicity_met": negative_counter_steps == 0,
    }
    screens = {
        "holdout_counter_recall_met": all(
            isinstance(holdout["by_bank"][bank]["counter_event_recall"], float)
            and holdout["by_bank"][bank]["counter_event_recall"]
            >= selected.minimum_holdout_counter_recall
            for bank in ("medium", "high")
        ),
        "holdout_pressure_precision_met": all(
            isinstance(holdout["by_bank"][bank]["pressure_event_precision"], float)
            and holdout["by_bank"][bank]["pressure_event_precision"]
            >= selected.minimum_holdout_pressure_precision
            for bank in ("medium", "high")
        ),
        "recall_stability_met": all(
            isinstance(recall_shift_by_bank[bank], float)
            and recall_shift_by_bank[bank] <= selected.maximum_recall_shift
            for bank in ("medium", "high")
        ),
        "holdout_median_absolute_offset_met": all(
            isinstance(
                holdout["by_bank"][bank]["absolute_time_offset_s"]["median"],
                (int, float),
            )
            and holdout["by_bank"][bank]["absolute_time_offset_s"]["median"]
            <= selected.maximum_holdout_median_absolute_offset_s
            for bank in ("medium", "high")
        ),
    }
    supported = all(eligibility.values()) and all(screens.values())
    return {
        "schema_version": 1,
        "artifact_type": "confidential_station_lifecycle_pressure_alignment_holdout",
        "evidence_role": "same_site_storage_recharge_event_alignment",
        "joint_alignment_outcomes_seen_before_freeze": False,
        "privacy": {
            "source_identifiers_published": False,
            "source_paths_published": False,
            "source_filenames_published": False,
            "source_headers_published": False,
            "per_file_hashes_published": False,
            "raw_rows_persisted": False,
            "absolute_timestamps_published": False,
            "calendar_dates_published": False,
            "site_company_location_manufacturer_published": False,
        },
        "files": {
            "pressure_files_read": pressure_files,
            "counter_files_read": counter_files,
            "exact_duplicate_files_excluded": duplicate_files,
        },
        "rows": {
            "pressure_rows_read": raw_pressure_rows,
            "counter_rows_read": raw_counter_rows,
            "rejected_rows": rejected_rows,
        },
        "counter_quality": {
            "negative_chronological_steps": negative_counter_steps,
        },
        "rules": {
            key: getattr(selected, key) for key in selected.__dataclass_fields__
        },
        "calibration": calibration,
        "holdout": holdout,
        "metrics": {"recall_shift_by_bank": recall_shift_by_bank},
        "eligibility": eligibility,
        "screens": screens,
        "decision": {
            "pressure_completion_counter_alignment_supported": supported,
            "recharge_event_detector_corroborated": supported,
            "runtime_parameter_application": False,
            "default_model_parameters_changed": False,
            "vehicle_fill_validation": False,
            "full_loop_holdout_eligible": False,
            "independent_external_validation": False,
        },
        "claim_boundary": (
            "Same-site storage recharge completion and owner-defined lifecycle-counter "
            "alignment only. It does not validate vehicle filling, compressor capacity, "
            "storage geometry, degradation rate, a safety limit, accident frequency, "
            "independent-site transfer, or field certification."
        ),
    }


__all__ = [
    "CounterEvent",
    "LifecyclePressureAlignmentRules",
    "evaluate_lifecycle_pressure_alignment",
]
