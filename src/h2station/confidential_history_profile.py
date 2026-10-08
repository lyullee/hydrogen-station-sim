"""Privacy-bounded profiling for long station history exports.

Source headers, paths, timestamps and rows stay outside the repository.  A
caller-supplied mapping identifies a header only by a one-way fingerprint and
maps numeric column positions to generic roles.  The result contains aggregate
statistics and explicit claim boundaries only.
"""

from __future__ import annotations

from collections import Counter, defaultdict
import csv
import hashlib
import math
from pathlib import Path
from statistics import median
from typing import Iterable, Mapping

from .confidential_signal_consistency import _delimiter, _encodings, _parse_time
from .controlled_station_replay import _quantile


def header_fingerprint(header: Iterable[str]) -> str:
    """Return a non-reversible fingerprint without retaining source labels."""

    column_hashes = (
        hashlib.sha256(str(value).encode("utf-8")).hexdigest()[:12]
        for value in header
    )
    return hashlib.sha256("|".join(column_hashes).encode("utf-8")).hexdigest()[:12]


def _rounded(value: float | None) -> float | None:
    return round(float(value), 6) if value is not None and math.isfinite(value) else None


def _stats(values: Iterable[float]) -> dict[str, float | int | None]:
    ordered = sorted(float(value) for value in values if math.isfinite(value))
    return {
        "count": len(ordered),
        "min": _rounded(ordered[0] if ordered else None),
        "p05": _rounded(_quantile(ordered, 0.05)),
        "median": _rounded(median(ordered) if ordered else None),
        "p95": _rounded(_quantile(ordered, 0.95)),
        "max": _rounded(ordered[-1] if ordered else None),
    }


def _finite(value: str) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def _schema_mapping(mapping: Mapping[str, object]) -> dict[str, Mapping[str, object]]:
    schemas = mapping.get("schemas")
    if not isinstance(schemas, list) or not schemas:
        raise ValueError("mapping must contain at least one schema")
    result: dict[str, Mapping[str, object]] = {}
    for schema in schemas:
        if not isinstance(schema, Mapping):
            raise ValueError("every schema mapping must be an object")
        fingerprint = str(schema.get("header_fingerprint") or "")
        schema_id = str(schema.get("schema_id") or "")
        channels = schema.get("numeric_channels")
        if len(fingerprint) != 12 or not schema_id or not isinstance(channels, list):
            raise ValueError("schema id, 12-character fingerprint and channels are required")
        if fingerprint in result:
            raise ValueError("schema header fingerprints must be unique")
        roles = [str(item.get("role") or "") for item in channels if isinstance(item, Mapping)]
        if len(roles) != len(channels) or not all(roles) or len(roles) != len(set(roles)):
            raise ValueError("numeric channel roles must be non-empty and unique")
        result[fingerprint] = schema
    return result


def _read_header(path: Path) -> tuple[str, str, list[str]] | None:
    prefix = path.open("rb").read(4096)
    for encoding in _encodings(prefix):
        try:
            with path.open("r", encoding=encoding, newline="") as handle:
                first = handle.readline()
            delimiter = _delimiter(first)
            header = next(csv.reader([first], delimiter=delimiter), [])
            if header:
                return encoding, delimiter, header
        except (UnicodeError, OSError, csv.Error):
            continue
    return None


def _summarize_split(
    rows: list[tuple[float, dict[str, float]]],
    *,
    roles: tuple[str, ...],
    stability_roles: tuple[str, ...],
    calibration_fraction: float,
) -> dict[str, object]:
    ordered = sorted(rows, key=lambda item: item[0])
    if len(ordered) < 2:
        calibration_rows = ordered
        holdout_rows: list[tuple[float, dict[str, float]]] = []
    else:
        split = max(1, min(len(ordered) - 1, int(len(ordered) * calibration_fraction)))
        calibration_rows = ordered[:split]
        holdout_rows = ordered[split:]

    def summarize(partition: list[tuple[float, dict[str, float]]]) -> dict[str, object]:
        return {
            role: _stats(values.get(role) for _, values in partition if role in values)
            for role in roles
        }

    calibration = summarize(calibration_rows)
    holdout = summarize(holdout_rows)
    inside = {}
    for role in stability_roles:
        lower = calibration.get(role, {}).get("p05")
        upper = calibration.get(role, {}).get("p95")
        observed = holdout.get(role, {}).get("median")
        inside[role] = (
            isinstance(lower, (int, float))
            and isinstance(upper, (int, float))
            and isinstance(observed, (int, float))
            and lower <= observed <= upper
        )
    return {
        "sampled_rows": len(ordered),
        "calibration_fraction": round(calibration_fraction, 6),
        "calibration": calibration,
        "holdout": holdout,
        "stability_roles": list(stability_roles),
        "holdout_medians_inside_calibration_p05_p95": inside,
        "stability_supported": bool(inside) and all(inside.values()),
    }


def analyze_confidential_history(
    input_path: Path,
    mapping: Mapping[str, object],
    *,
    sample_stride: int = 600,
    calibration_fraction: float = 0.70,
) -> dict[str, object]:
    """Profile mapped nine-column exports without returning source identifiers."""

    if sample_stride < 1:
        raise ValueError("sample_stride must be positive")
    if not 0.5 <= calibration_fraction < 1.0:
        raise ValueError("calibration_fraction must be in [0.5, 1.0)")
    schema_by_fingerprint = _schema_mapping(mapping)
    observations: dict[str, list[tuple[float, dict[str, float]]]] = defaultdict(list)
    file_counts: Counter[str] = Counter()
    raw_rows: Counter[str] = Counter()
    rejected_samples: Counter[str] = Counter()
    sample_periods: list[float] = []
    time_extents: dict[str, list[float]] = defaultdict(list)

    for path in sorted(Path(input_path).rglob("*.csv")):
        header_record = _read_header(path)
        if header_record is None:
            continue
        encoding, delimiter, header = header_record
        schema = schema_by_fingerprint.get(header_fingerprint(header))
        if schema is None:
            continue
        schema_id = str(schema["schema_id"])
        timestamp_index = int(schema.get("timestamp_index", 0))
        skip_rows = int(schema.get("skip_rows_after_header", 1))
        channels = tuple(
            (str(item["role"]), int(item["index"]))
            for item in schema["numeric_channels"]  # type: ignore[index]
        )
        times: list[float] = []
        with path.open("r", encoding=encoding, newline="") as handle:
            handle.readline()
            for _ in range(skip_rows):
                handle.readline()
            for row_number, line in enumerate(handle):
                raw_rows[schema_id] += 1
                if row_number % sample_stride:
                    continue
                try:
                    row = next(csv.reader([line], delimiter=delimiter))
                except csv.Error:
                    rejected_samples[schema_id] += 1
                    continue
                if timestamp_index >= len(row):
                    rejected_samples[schema_id] += 1
                    continue
                time_s = _parse_time(row[timestamp_index])
                values: dict[str, float] = {}
                for role, index in channels:
                    if index >= len(row):
                        continue
                    value = _finite(row[index])
                    if value is not None:
                        values[role] = value
                if time_s is None or len(values) != len(channels):
                    rejected_samples[schema_id] += 1
                    continue
                timestamp = float(time_s)
                times.append(timestamp)
                observations[schema_id].append((timestamp, values))
        file_counts[schema_id] += 1
        if times:
            time_extents[schema_id].extend((min(times), max(times)))
            deltas = [abs(after - before) for before, after in zip(times, times[1:]) if after != before]
            if deltas:
                sample_periods.append(median(deltas) / sample_stride)

    schema_results: dict[str, object] = {}
    all_stable = True
    quality_warnings: list[str] = []
    for schema in schema_by_fingerprint.values():
        schema_id = str(schema["schema_id"])
        roles = tuple(str(item["role"]) for item in schema["numeric_channels"])  # type: ignore[index]
        stability_roles = tuple(str(role) for role in schema.get("stability_roles", roles))
        result = _summarize_split(
            observations.get(schema_id, []),
            roles=roles,
            stability_roles=stability_roles,
            calibration_fraction=calibration_fraction,
        )
        ordered_groups = schema.get("ordered_role_groups") or []
        order_checks: dict[str, float] = {}
        for group_index, group in enumerate(ordered_groups, start=1):
            role_group = tuple(str(role) for role in group)
            eligible = [
                values for _, values in observations.get(schema_id, [])
                if all(role in values for role in role_group)
            ]
            ordered_count = sum(
                all(values[left] <= values[right] for left, right in zip(role_group, role_group[1:]))
                for values in eligible
            )
            order_checks[f"ordered_group_{group_index}"] = round(
                ordered_count / max(len(eligible), 1), 6
            )
        plausible_ranges = schema.get("plausible_ranges") or {}
        plausible_checks: dict[str, float] = {}
        for role, bounds in plausible_ranges.items():
            lower, upper = float(bounds[0]), float(bounds[1])
            values = [
                row_values[str(role)]
                for _, row_values in observations.get(schema_id, [])
                if str(role) in row_values
            ]
            plausible_checks[str(role)] = round(
                sum(lower <= value <= upper for value in values) / max(len(values), 1), 6
            )
        result.update(
            {
                "files_read": file_counts[schema_id],
                "raw_data_rows": raw_rows[schema_id],
                "rejected_sample_rows": rejected_samples[schema_id],
                "order_checks": order_checks,
                "plausible_range_fractions": plausible_checks,
            }
        )
        schema_results[schema_id] = result
        all_stable = all_stable and bool(result["stability_supported"])
        if not result["sampled_rows"]:
            quality_warnings.append(f"no_samples:{schema_id}")

    extents = [values for values in time_extents.values() if len(values) >= 2]
    overlap_fraction: float | None = None
    if len(extents) >= 2:
        starts = [min(values) for values in extents]
        ends = [max(values) for values in extents]
        overlap = max(0.0, min(ends) - max(starts))
        union = max(ends) - min(starts)
        overlap_fraction = overlap / union if union > 0.0 else None
    median_period = median(sample_periods) if sample_periods else None
    station_side_supported = (
        sum(raw_rows.values()) > 1_000_000
        and median_period is not None
        and 0.5 <= median_period <= 2.0
        and overlap_fraction is not None
        and overlap_fraction >= 0.95
        and all_stable
        and not quality_warnings
    )
    attestation = dict(mapping.get("attestation") or {})
    return {
        "schema_version": 1,
        "artifact_type": "confidential_station_longitudinal_history_diagnostic",
        "raw_rows_persisted": False,
        "source_identifiers_published": False,
        "source_paths_published": False,
        "source_filenames_published": False,
        "absolute_timestamps_published": False,
        "calendar_dates_published": False,
        "files_read": sum(file_counts.values()),
        "raw_data_rows": sum(raw_rows.values()),
        "sample_stride": sample_stride,
        "sampled_rows": sum(len(rows) for rows in observations.values()),
        "median_sample_period_s": _rounded(median_period),
        "schema_coverage_overlap_fraction": _rounded(overlap_fraction),
        "schemas": schema_results,
        "quality_warnings": quality_warnings,
        "attestation": attestation,
        "eligibility": {
            "station_side_longitudinal_diagnostic_supported": station_side_supported,
            "runtime_parameter_application": False,
            "vehicle_fill_validation": False,
            "full_loop_holdout_eligible": False,
            "default_model_parameters_changed": False,
        },
        "claim_boundary": (
            "Exploratory longitudinal station-side diagnostic. Generic flow/totalizer "
            "and temperature mappings remain hypotheses unless separately attested; "
            "no raw rows, tags, paths, filenames or calendar dates are published. It "
            "does not validate vehicle filling, safety limits or consequence distances."
        ),
    }


__all__ = ["analyze_confidential_history", "header_fingerprint"]
