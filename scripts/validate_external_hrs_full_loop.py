"""Screen a synchronized external HRS station-to-vehicle trace.

This is a pre-evaluation quality gate.  It consumes a CSV that has already
passed the byte-level intake and metadata eligibility checks, then verifies
that the station, vehicle, source-bank and protection-state channels share a
single monotonic clock.  It deliberately does not impute, resample, smooth,
fit, or score the digital twin.

The result ``FULL_LOOP_TRACE_READY_FOR_EVALUATION`` means only that the trace
is a usable input for a separately frozen numerical evaluator.  It is not a
validation result, a safety claim, or evidence that the IJHE readiness gate is
closed.
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Iterable

from validate_external_hrs_trace import (
    DEFAULT_ALIASES,
    _finite_float,
    _mapped_column,
    validate_trace,
)


# The aliases intentionally describe engineering meaning rather than private
# tag names.  A custodian may provide a declaration ``column_map`` for names
# that are not in this list; no source/site identifier is stored in the result.
FULL_LOOP_ALIASES: dict[str, tuple[str, ...]] = {
    "station_pressure_mpa_abs": (
        "station_pressure_mpa_abs",
        "dispenser_pressure_mpa_abs",
        "gas_path_pressure_mpa_abs",
    ),
    "delivered_gas_temperature_degC": (
        "delivered_gas_temperature_degC",
        "dispenser_gas_temperature_degC",
        "gas_delivery_temperature_degC",
    ),
    "cascade_source_pressure_mpa_abs": (
        "cascade_source_pressure_mpa_abs",
        "source_bank_pressure_mpa_abs",
        "cascade_pressure_mpa_abs",
    ),
    "cascade_selected_bank": (
        "cascade_selected_bank",
        "selected_bank",
        "source_bank",
    ),
    "compressor_state": ("compressor_state", "compressor_status"),
    "precooler_state": ("precooler_state", "precooler_status"),
    "leak_check_state": ("leak_check_state", "leak_check_status"),
    "vent_state": ("vent_state", "vent_status"),
    "fault_state": ("fault_state", "fault_status"),
    "esd_state": ("esd_state", "esd_status"),
}

_NUMERIC_CHANNELS = {
    "station_pressure_mpa_abs": (0.0, 150.0),
    "cascade_source_pressure_mpa_abs": (0.0, 150.0),
    "delivered_gas_temperature_degC": (-100.0, 250.0),
}


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _column(
    header: Iterable[str], canonical: str, declaration: dict[str, Any]
) -> str | None:
    columns = declaration.get("column_map")
    if isinstance(columns, dict) and isinstance(columns.get(canonical), str):
        mapped = columns[canonical]
        if mapped in header:
            return mapped
    aliases = FULL_LOOP_ALIASES.get(canonical)
    if aliases is not None:
        header_set = set(header)
        return next((alias for alias in aliases if alias in header_set), None)
    return _mapped_column(header, canonical, declaration)


def _state_missing(value: str | None) -> bool:
    if value is None:
        return True
    # ``none`` is a valid fault-state value (no active fault); only explicit
    # missing-value markers are rejected.
    return value.strip().lower() in {"", "na", "n/a", "nan", "null", "-"}


def validate_full_loop_trace(
    trace_path: Path,
    manifest_path: Path,
    declaration_path: Path,
    protocol_path: Path,
    *,
    bundle_root: Path | None = None,
) -> dict[str, Any]:
    """Return a deterministic full-loop channel and clock-screen report."""

    base = validate_trace(
        trace_path,
        manifest_path,
        declaration_path,
        protocol_path,
        bundle_root=bundle_root,
    )
    claim_boundary = (
        "A full-loop input screen is not model validation, safety evidence, "
        "or an IJHE completion result."
    )
    if base.get("decision") not in {"QUALITY_SCREEN_PASS"}:
        return {
            "schema_version": 1,
            "decision": "INELIGIBLE_BASE_TRACE_SCREEN",
            "full_loop_trace_ready": False,
            "numerical_values_inspected": base.get("numerical_values_inspected", False),
            "base_trace_screen": base,
            "claim_boundary": claim_boundary,
            "reasons": ["base external HRS trace screen did not pass"],
        }

    declaration = _json(declaration_path)
    limits = _json(protocol_path).get("trace_quality") or {}
    min_rows = int(limits.get("minimum_rows", 20))
    max_missing_fraction = float(limits.get("max_missing_fraction", 0.01))
    max_gap_s = float(limits.get("max_gap_s", 60.0))

    with trace_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        header = tuple(reader.fieldnames or ())
        rows = list(reader)

    required = (
        "station_pressure_mpa_abs",
        "delivered_gas_temperature_degC",
        "cascade_source_pressure_mpa_abs",
        "cascade_selected_bank",
        "compressor_state",
        "precooler_state",
        "leak_check_state",
        "vent_state",
        "fault_state",
        "esd_state",
    )
    mapped = {name: _column(header, name, declaration) for name in required}
    reasons: list[str] = []
    missing_columns = [name for name, column in mapped.items() if column is None]
    if missing_columns:
        reasons.append("missing full-loop trace columns: " + ", ".join(missing_columns))
        return {
            "schema_version": 1,
            "decision": "FULL_LOOP_TRACE_NOT_READY",
            "full_loop_trace_ready": False,
            "numerical_values_inspected": True,
            "base_trace_screen": base,
            "columns": mapped,
            "observed": {"rows": len(rows)},
            "claim_boundary": claim_boundary,
            "reasons": reasons,
        }

    time_column = _column(header, "time_s", declaration)
    if time_column is None:
        reasons.append("missing common time column")
        time_column = ""

    missing_rows = 0
    times: list[float] = []
    numeric_values: dict[str, list[float]] = {name: [] for name in _NUMERIC_CHANNELS}
    state_values: dict[str, set[str]] = {name: set() for name in required if name not in _NUMERIC_CHANNELS}
    for row in rows:
        time_value = _finite_float(row.get(time_column, "")) if time_column else None
        values_ok = time_value is not None
        if time_value is not None:
            times.append(time_value)
        for name, column in mapped.items():
            raw = row.get(column or "")
            if name in _NUMERIC_CHANNELS:
                value = _finite_float(raw or "")
                if value is None:
                    values_ok = False
                else:
                    numeric_values[name].append(value)
            else:
                if _state_missing(raw):
                    values_ok = False
                else:
                    state_values[name].add(raw.strip())
        if not values_ok:
            missing_rows += 1

    if len(rows) < min_rows:
        reasons.append(f"trace has {len(rows)} rows; minimum is {min_rows}")
    if rows and missing_rows / len(rows) > max_missing_fraction:
        reasons.append(
            f"full-loop required-channel missing/non-finite fraction "
            f"{missing_rows / len(rows):.4f} exceeds {max_missing_fraction:.4f}"
        )
    if len(times) >= 2:
        gaps = [right - left for left, right in zip(times, times[1:])]
        if any(gap <= 0.0 for gap in gaps):
            reasons.append("common time base is not strictly increasing")
        positive_gaps = [gap for gap in gaps if gap > 0.0]
        if positive_gaps and max(positive_gaps) > max_gap_s:
            reasons.append(f"maximum full-loop time gap exceeds {max_gap_s:g} s")
    for name, values in numeric_values.items():
        low, high = _NUMERIC_CHANNELS[name]
        if values and not all(low < value <= high if low == 0.0 else low <= value <= high for value in values):
            reasons.append(f"{name} value outside the frozen physical range")

    return {
        "schema_version": 1,
        "decision": "FULL_LOOP_TRACE_READY_FOR_EVALUATION" if not reasons else "FULL_LOOP_TRACE_NOT_READY",
        "full_loop_trace_ready": not reasons,
        "numerical_values_inspected": True,
        "base_trace_screen": {
            "decision": base.get("decision"),
            "trace": base.get("trace"),
            "manifest": base.get("intake"),
        },
        "columns": {"time_s": time_column, **mapped},
        "observed": {
            "rows": len(rows),
            "rows_with_missing_or_nonfinite_required_values": missing_rows,
            "time_start_s": min(times) if times else None,
            "time_end_s": max(times) if times else None,
            "numeric_min_max": {
                name: [min(values), max(values)] if values else [None, None]
                for name, values in numeric_values.items()
            },
            "state_distinct_values": {
                name: sorted(values) for name, values in state_values.items()
            },
        },
        "claim_boundary": claim_boundary,
        "no_imputation_or_resampling": True,
        "reasons": reasons,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trace", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--declaration", type=Path, required=True)
    parser.add_argument(
        "--protocol", type=Path, default=Path("research/external_hrs_intake_protocol.json")
    )
    parser.add_argument("--bundle-root", type=Path, default=None)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = validate_full_loop_trace(
        args.trace,
        args.manifest,
        args.declaration,
        args.protocol,
        bundle_root=args.bundle_root,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output)
    return 0 if result.get("full_loop_trace_ready") else 2


if __name__ == "__main__":
    raise SystemExit(main())
