"""Privacy-bounded consistency screening for confidential station loggers.

The routines in this module discover only generic time, pressure and flow-like
columns.  Source paths, filenames, headers, timestamps and raw values stay in
memory and are never included in the serialized result.  A positive screen is
therefore a request for a custodian unit/role attestation, not permission to
interpret an unlabelled channel as physical mass flow.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timezone
import math
from pathlib import Path
import re
from statistics import median
from typing import Iterable, Iterator

import numpy as np


_TIME_TERMS = ("time", "date", "timestamp", "clock", "local", "시간", "일시", "시각")
_PRESSURE_TERMS = ("pressure", "press", "압력")
_FLOW_TERMS = ("flow", "mass", "rate", "total", "acc", "유량", "질량", "적산")
_PRESSURE_TAG = re.compile(r"(?:^|[._\s-])(?:pt|pi)(?:$|[._\s-]|\d)", re.I)
_FLOW_TAG = re.compile(r"(?:^|[._\s-])(?:ft|fqi|mfm|fwg)(?:$|[._\s-]|\d)", re.I)
_TIME_FORMATS = (
    "%Y-%m-%d %H:%M:%S",
    "%Y/%m/%d %H:%M:%S",
    "%m/%d/%Y %I:%M:%S %p",
    "%m/%d/%Y %I:%M:%S.%f %p",
    "%m/%d/%Y %H:%M:%S",
    "%m/%d/%Y %H:%M:%S.%f",
    "%Y %m %d %H:%M:%S",
    "%Y %m %d %H:%M:%S.%f",
)


@dataclass(frozen=True)
class _Table:
    time: np.ndarray
    pressures: tuple[np.ndarray, ...]
    flows: tuple[np.ndarray, ...]
    rows_read: int


@dataclass(frozen=True)
class _PairResult:
    correlation: float
    normalized_rmse_percent: float
    scale: float
    active_samples: int

    @property
    def strong(self) -> bool:
        return (
            self.active_samples >= 30
            and self.correlation >= 0.80
            and self.normalized_rmse_percent <= 35.0
            and abs(self.scale) > 0.0
        )


def _finite(value: object) -> float | None:
    try:
        parsed = float(str(value).strip())
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def _parse_time(value: object) -> float | None:
    if value is None:
        return None
    text = str(value).strip().strip("\ufeff")
    if not text:
        return None
    numeric = _finite(text)
    if numeric is not None:
        return numeric
    normalized = text.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.timestamp()
    except ValueError:
        pass
    for format_string in _TIME_FORMATS:
        try:
            return datetime.strptime(text, format_string).replace(
                tzinfo=timezone.utc,
            ).timestamp()
        except ValueError:
            pass
    return None


def _encodings(prefix: bytes) -> tuple[str, ...]:
    if prefix.startswith((b"\xff\xfe", b"\xfe\xff")):
        return ("utf-16", "utf-16le", "utf-16be", "utf-8-sig", "cp949")
    if prefix and prefix.count(b"\x00") >= max(2, len(prefix) // 8):
        return ("utf-16le", "utf-16be", "utf-16", "utf-8-sig", "cp949")
    return ("utf-8-sig", "utf-8", "cp949", "euc-kr")


def _delimiter(line: str) -> str:
    candidates = (",", ";", "\t")
    return max(candidates, key=line.count)


def _indices(header: list[str], terms: tuple[str, ...], pattern: re.Pattern[str] | None = None) -> tuple[int, ...]:
    result = []
    for index, value in enumerate(header):
        compact = value.strip().casefold()
        if any(term.casefold() in compact for term in terms) or (
            pattern is not None and pattern.search(compact)
        ):
            result.append(index)
    return tuple(result)


def _header_candidate(rows: list[list[str]]) -> tuple[int, list[str]] | None:
    best: tuple[tuple[int, int, int], int, list[str]] | None = None
    for index, row in enumerate(rows[:40]):
        time_count = len(_indices(row, _TIME_TERMS))
        pressure_count = len(_indices(row, _PRESSURE_TERMS, _PRESSURE_TAG))
        flow_count = len(_indices(row, _FLOW_TERMS, _FLOW_TAG))
        score = (
            int(bool(time_count)) + int(bool(pressure_count)) + int(bool(flow_count)),
            pressure_count + flow_count,
            -index,
        )
        if best is None or score > best[0]:
            best = (score, index, row)
    if best is None or best[0][0] < 2:
        return None
    return best[1], best[2]


def _iter_rows(path: Path) -> Iterator[tuple[list[str], Iterable[list[str]]]]:
    try:
        with path.open("rb") as binary:
            prefix = binary.read(4096)
    except OSError:
        return
    for encoding in _encodings(prefix):
        try:
            handle = path.open("r", encoding=encoding, newline="")
            first_lines = []
            for _ in range(40):
                line = handle.readline()
                if not line:
                    break
                first_lines.append(line)
            handle.seek(0)
            delimiter = _delimiter(first_lines[0] if first_lines else "")
            reader = csv.reader(handle, delimiter=delimiter)
            buffered = [row for _, row in zip(range(40), reader)]
            selected = _header_candidate(buffered)
            if selected is None:
                handle.close()
                return
            header_index, header = selected
            handle.seek(0)
            reader = csv.reader(handle, delimiter=delimiter)
            for _ in range(header_index + 1):
                next(reader, None)
            try:
                yield header, reader
            finally:
                handle.close()
            return
        except (UnicodeError, OSError, csv.Error):
            try:
                handle.close()
            except (NameError, OSError):
                pass
            continue


def _read_table(path: Path, *, max_rows: int, stride: int) -> _Table | None:
    streamed = _iter_rows(path)
    try:
        header, rows = next(streamed)
    except StopIteration:
        return None
    time_indices = _indices(header, _TIME_TERMS)
    pressure_indices = _indices(header, _PRESSURE_TERMS, _PRESSURE_TAG)
    flow_indices = _indices(header, _FLOW_TERMS, _FLOW_TAG)
    if not pressure_indices or len(flow_indices) < 2:
        streamed.close()
        return None
    time_index = time_indices[0] if time_indices else 0
    times: list[float] = []
    pressures: list[list[float]] = [[] for _ in pressure_indices]
    flows: list[list[float]] = [[] for _ in flow_indices]
    rows_read = 0
    try:
        for source_index, row in enumerate(rows):
            if source_index % stride:
                continue
            if rows_read >= max_rows:
                break
            maximum_index = max(time_index, *pressure_indices, *flow_indices)
            if len(row) <= maximum_index:
                continue
            timestamp = _parse_time(row[time_index])
            pressure_values = [_finite(row[index]) for index in pressure_indices]
            flow_values = [_finite(row[index]) for index in flow_indices]
            if timestamp is None:
                continue
            times.append(timestamp)
            for target, value in zip(pressures, pressure_values):
                target.append(float("nan") if value is None else value)
            for target, value in zip(flows, flow_values):
                target.append(float("nan") if value is None else value)
            rows_read += 1
    finally:
        streamed.close()
    if len(times) < 40:
        return None
    order = np.argsort(np.asarray(times, dtype=float), kind="stable")
    sorted_time = np.asarray(times, dtype=float)[order]
    return _Table(
        time=sorted_time,
        pressures=tuple(np.asarray(values, dtype=float)[order] for values in pressures),
        flows=tuple(np.asarray(values, dtype=float)[order] for values in flows),
        rows_read=rows_read,
    )


def _monotonic_fraction(values: np.ndarray) -> float:
    finite = values[np.isfinite(values)]
    if finite.size < 3:
        return 0.0
    differences = np.diff(finite)
    tolerance = max(float(np.nanmax(finite) - np.nanmin(finite)), 1.0) * 1.0e-10
    return float(np.mean(differences >= -tolerance))


def _variable(values: np.ndarray) -> bool:
    finite = values[np.isfinite(values)]
    if finite.size < 40:
        return False
    span = float(np.nanmax(finite) - np.nanmin(finite))
    scale = max(float(np.nanmedian(np.abs(finite))), 1.0)
    return span > scale * 1.0e-6


def _compare_pair(time_s: np.ndarray, cumulative: np.ndarray, instantaneous: np.ndarray) -> _PairResult | None:
    valid = np.isfinite(time_s) & np.isfinite(cumulative) & np.isfinite(instantaneous)
    time_s = time_s[valid]
    cumulative = cumulative[valid]
    instantaneous = instantaneous[valid]
    if time_s.size < 40:
        return None
    dt = np.diff(time_s)
    delta = np.diff(cumulative)
    signal = 0.5 * (instantaneous[:-1] + instantaneous[1:])
    tolerance = max(float(np.ptp(cumulative)), 1.0) * 1.0e-10
    usable = (dt > 0.0) & (delta >= -tolerance) & np.isfinite(signal)
    derivative = np.divide(delta, dt, out=np.zeros_like(delta), where=usable)
    derivative = derivative[usable]
    signal = signal[usable]
    if derivative.size < 30:
        return None
    derivative_threshold = max(float(np.nanpercentile(np.abs(derivative), 20)), 1.0e-12)
    signal_threshold = max(float(np.nanpercentile(np.abs(signal), 20)), 1.0e-12)
    active = (np.abs(derivative) > derivative_threshold) | (np.abs(signal) > signal_threshold)
    derivative = derivative[active]
    signal = signal[active]
    if derivative.size < 30 or np.std(signal) <= 0.0 or np.std(derivative) <= 0.0:
        return None
    denominator = float(np.dot(signal, signal))
    if denominator <= 0.0:
        return None
    scale = float(np.dot(signal, derivative) / denominator)
    predicted = scale * signal
    if np.std(predicted) <= 0.0:
        return None
    correlation = float(np.corrcoef(derivative, predicted)[0, 1])
    reference_span = max(float(np.nanpercentile(derivative, 95) - np.nanpercentile(derivative, 5)), 1.0e-12)
    nrmse = float(np.sqrt(np.mean((derivative - predicted) ** 2)) / reference_span * 100.0)
    if not all(math.isfinite(value) for value in (scale, correlation, nrmse)):
        return None
    return _PairResult(correlation, nrmse, scale, int(derivative.size))


def _quantile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    return float(np.quantile(np.asarray(values, dtype=float), fraction))


def audit_confidential_signal_consistency(
    root: Path,
    *,
    max_rows_per_file: int = 200_000,
    stride: int = 1,
) -> dict[str, object]:
    """Return a de-identified pressure/flow consistency screen for CSV logs."""

    if max_rows_per_file < 100 or stride < 1:
        raise ValueError("max_rows_per_file must be >= 100 and stride must be >= 1")
    files = sorted(path for path in root.rglob("*.csv") if path.is_file())
    tables_read = 0
    sampled_rows = 0
    pressure_channels = 0
    flow_channels = 0
    cumulative_candidates = 0
    instantaneous_candidates = 0
    pairs: list[_PairResult] = []
    files_with_strong_pair = 0
    for path in files:
        table = _read_table(path, max_rows=max_rows_per_file, stride=stride)
        if table is None:
            continue
        tables_read += 1
        sampled_rows += table.rows_read
        pressure_channels += sum(_variable(values) for values in table.pressures)
        variable_flows = tuple(values for values in table.flows if _variable(values))
        flow_channels += len(variable_flows)
        cumulative = tuple(
            values for values in variable_flows if _monotonic_fraction(values) >= 0.995
        )
        instantaneous = tuple(
            values for values in variable_flows if _monotonic_fraction(values) < 0.995
        )
        cumulative_candidates += len(cumulative)
        instantaneous_candidates += len(instantaneous)
        table_pairs = [
            result
            for totalizer in cumulative
            for signal in instantaneous
            if (result := _compare_pair(table.time, totalizer, signal)) is not None
        ]
        pairs.extend(table_pairs)
        files_with_strong_pair += int(any(result.strong for result in table_pairs))
    strong = [result for result in pairs if result.strong]
    candidate_correlations = [result.correlation for result in pairs]
    candidate_errors = [result.normalized_rmse_percent for result in pairs]
    correlations = [result.correlation for result in strong]
    errors = [result.normalized_rmse_percent for result in strong]
    scales = [result.scale for result in strong]
    return {
        "schema_version": 1,
        "artifact_type": "confidential_station_signal_consistency_screen",
        "analysis_status": "pre_attestation_internal_consistency_screen",
        "evidence_scope": "owner_controlled_confidential_station_side_archive",
        "privacy": {
            "source_identifiers_published": False,
            "source_paths_published": False,
            "filenames_published": False,
            "tag_names_published": False,
            "raw_rows_persisted": False,
            "exact_timestamps_published": False,
            "manufacturer_or_model_published": False,
        },
        "screen": {
            "csv_files_discovered": len(files),
            "pressure_flow_tables_read": tables_read,
            "sampled_rows": sampled_rows,
            "variable_pressure_channels": pressure_channels,
            "variable_flow_like_channels": flow_channels,
            "cumulative_flow_like_candidates": cumulative_candidates,
            "instantaneous_flow_like_candidates": instantaneous_candidates,
            "candidate_pairs_evaluated": len(pairs),
            "strong_consistency_pairs": len(strong),
            "files_with_strong_consistency_pair": files_with_strong_pair,
            "candidate_pair_aggregate": {
                "correlation_median": median(candidate_correlations) if candidate_correlations else None,
                "correlation_max": max(candidate_correlations) if candidate_correlations else None,
                "normalized_rmse_percent_median": median(candidate_errors) if candidate_errors else None,
                "normalized_rmse_percent_min": min(candidate_errors) if candidate_errors else None,
                "negative_scale_pair_count": sum(result.scale < 0.0 for result in pairs),
                "active_samples_median": median(
                    [result.active_samples for result in pairs]
                ) if pairs else None,
            },
            "strong_pair_aggregate": {
                "correlation_median": median(correlations) if correlations else None,
                "correlation_p10": _quantile(correlations, 0.10),
                "normalized_rmse_percent_median": median(errors) if errors else None,
                "normalized_rmse_percent_p90": _quantile(errors, 0.90),
                "derivative_to_signal_scale_median": median(scales) if scales else None,
                "scale_is_dimensionless_or_physical": False,
            },
        },
        "attestation": {
            "channel_roles_attested": False,
            "flow_units_attested": False,
            "totalizer_reset_semantics_attested": False,
            "calibration_status_attested": False,
        },
        "eligibility": {
            "flow_channel_pair_attestation_candidate": bool(strong),
            "absolute_mass_flow_supported": False,
            "conditional_bank_inventory_estimation_supported": False,
            "full_station_vehicle_validation": False,
            "independent_holdout": False,
        },
        "next_action": (
            "A data custodian must identify the generic instantaneous/totalizer pair, "
            "its engineering units, sign/reset convention and calibration status before "
            "the scale or any storage-volume estimate is used by the physical model."
        ),
        "claim_boundary": (
            "De-identified station-side signal-consistency screening only. Correlation "
            "between unlabelled channels does not attest their physical role or unit, "
            "validate the station-to-vehicle model, establish a safety limit or certify operation."
        ),
    }
