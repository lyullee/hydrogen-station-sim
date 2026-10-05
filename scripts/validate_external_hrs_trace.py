"""Run the frozen, metadata-gated quality screen for an external HRS CSV trace.

This is the first numerical read after byte-level intake.  It does not impute,
resample, smooth, fit or score a model.  A pass only means that the trace has a
usable common time base and declared channels for a later frozen evaluator.
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Iterable

from validate_external_hrs_manifest import validate as validate_manifest


DEFAULT_ALIASES = {
    "time_s": ("time_s", "time", "timestamp_s", "elapsed_s"),
    "pressure_mpa_abs": (
        "vehicle_pressure_mpa_abs",
        "receptacle_pressure_mpa_abs",
        "vehicle_or_receptacle_pressure_mpa_abs",
        "pressure_mpa_abs",
    ),
    "temperature_degC": (
        "gas_temperature_degC",
        "tank_temperature_degC",
        "gas_or_tank_temperature_degC",
        "temperature_degC",
    ),
    "mass_flow_g_s": ("mass_flow_g_s", "mass_flow", "flow_g_s"),
    "transferred_mass_kg": ("transferred_mass_kg", "cumulative_mass_kg"),
}


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _finite_float(value: str) -> float | None:
    try:
        number = float(value.strip())
    except (AttributeError, ValueError):
        return None
    return number if number == number and abs(number) != float("inf") else None


def _mapped_column(
    header: Iterable[str], canonical: str, declaration: dict[str, Any]
) -> str | None:
    columns = declaration.get("column_map")
    if isinstance(columns, dict) and isinstance(columns.get(canonical), str):
        mapped = columns[canonical]
        if mapped in header:
            return mapped
    for alias in DEFAULT_ALIASES.get(canonical, (canonical,)):
        if alias in header:
            return alias
    return None


def _relative_trace_path(trace_path: Path, root: Path) -> str:
    try:
        return trace_path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError as exc:
        raise ValueError("trace is outside the quarantined bundle root") from exc


def validate_trace(
    trace_path: Path,
    manifest_path: Path,
    declaration_path: Path,
    protocol_path: Path,
    *,
    bundle_root: Path | None = None,
) -> dict[str, Any]:
    """Return a deterministic, non-model trace-quality decision."""

    declaration = _json(declaration_path)
    protocol = _json(protocol_path)
    intake = validate_manifest(
        manifest_path, declaration_path, protocol_path, bundle_root=bundle_root
    )
    if not intake["eligible_for_numerical_evaluation"]:
        return {
            "schema_version": 1,
            "decision": "INELIGIBLE_INTAKE_METADATA",
            "numerical_values_inspected": False,
            "intake": intake,
            "claim_boundary": "Trace quality is not model validation or an IJHE completion result.",
            "reasons": list(intake["reasons"]),
        }

    root = Path(intake["integrity"]["source_root"])
    relative_path = _relative_trace_path(trace_path, root)
    manifest_records = {
        record.get("relative_path"): record
        for record in (_json(manifest_path).get("files") or [])
        if isinstance(record, dict)
    }
    if relative_path not in manifest_records:
        return {
            "schema_version": 1,
            "decision": "INELIGIBLE_TRACE_NOT_IN_MANIFEST",
            "numerical_values_inspected": False,
            "intake": intake,
            "claim_boundary": "Trace quality is not model validation or an IJHE completion result.",
            "reasons": [f"trace is not listed in intake manifest: {relative_path}"],
        }

    limits = protocol.get("trace_quality") or {}
    min_rows = int(limits.get("minimum_rows", 20))
    max_missing_fraction = float(limits.get("max_missing_fraction", 0.01))
    max_gap_s = float(limits.get("max_gap_s", 60.0))
    pressure_range = tuple(float(x) for x in limits.get("pressure_range_mpa_abs", [0.0, 150.0]))
    temperature_range = tuple(float(x) for x in limits.get("temperature_range_degC", [-100.0, 250.0]))
    flow_range = tuple(float(x) for x in limits.get("mass_flow_range_g_s", [-1000.0, 1000.0]))
    reasons: list[str] = []
    with trace_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        header = tuple(reader.fieldnames or ())
        time_column = _mapped_column(header, "time_s", declaration)
        pressure_column = _mapped_column(header, "pressure_mpa_abs", declaration)
        temperature_column = _mapped_column(header, "temperature_degC", declaration)
        flow_column = _mapped_column(header, "mass_flow_g_s", declaration)
        mass_column = _mapped_column(header, "transferred_mass_kg", declaration)
        missing_columns = []
        for name, column in (
            ("time_s", time_column),
            ("pressure_mpa_abs", pressure_column),
            ("temperature_degC", temperature_column),
        ):
            if column is None:
                missing_columns.append(name)
        if flow_column is None and mass_column is None:
            missing_columns.append("mass_flow_g_s|transferred_mass_kg")
        if missing_columns:
            return {
                "schema_version": 1,
                "decision": "INELIGIBLE_TRACE_CHANNELS",
                "numerical_values_inspected": True,
                "intake": intake,
                "columns": {"header": list(header)},
                "claim_boundary": "Trace quality is not model validation or an IJHE completion result.",
                "reasons": [f"missing required trace columns: {', '.join(missing_columns)}"],
            }

        rows = list(reader)
    row_count = len(rows)
    if row_count < min_rows:
        reasons.append(f"trace has {row_count} rows; minimum is {min_rows}")

    times: list[float] = []
    pressures: list[float] = []
    temperatures: list[float] = []
    flow_values: list[float] = []
    missing_required = 0
    for row_index, row in enumerate(rows, start=2):
        time_value = _finite_float(row.get(time_column, ""))
        pressure_value = _finite_float(row.get(pressure_column, ""))
        temperature_value = _finite_float(row.get(temperature_column, ""))
        flow_or_mass = _finite_float(row.get(flow_column, "")) if flow_column else _finite_float(row.get(mass_column, ""))
        if any(value is None for value in (time_value, pressure_value, temperature_value, flow_or_mass)):
            missing_required += 1
            continue
        times.append(time_value)  # type: ignore[arg-type]
        pressures.append(pressure_value)  # type: ignore[arg-type]
        temperatures.append(temperature_value)  # type: ignore[arg-type]
        flow_values.append(flow_or_mass)  # type: ignore[arg-type]
    if row_count and missing_required / row_count > max_missing_fraction:
        reasons.append(
            f"required-channel missing/non-finite fraction {missing_required / row_count:.4f} exceeds {max_missing_fraction:.4f}"
        )
    if len(times) >= 2:
        gaps = [right - left for left, right in zip(times, times[1:])]
        if any(gap <= 0.0 for gap in gaps):
            reasons.append("time base is not strictly increasing")
        positive_gaps = [gap for gap in gaps if gap > 0.0]
        if positive_gaps and max(positive_gaps) > max_gap_s:
            reasons.append(f"maximum time gap exceeds {max_gap_s:g} s")
    elif row_count >= min_rows:
        reasons.append("fewer than two finite rows remain after quality screening")
    if pressures and not all(pressure_range[0] < value <= pressure_range[1] for value in pressures):
        reasons.append("pressure value outside the frozen absolute-pressure range")
    if temperatures and not all(temperature_range[0] <= value <= temperature_range[1] for value in temperatures):
        reasons.append("temperature value outside the frozen range")
    if flow_values and not all(flow_range[0] <= value <= flow_range[1] for value in flow_values):
        reasons.append("mass-flow/transferred-mass value outside the frozen range")

    return {
        "schema_version": 1,
        "decision": "QUALITY_SCREEN_PASS" if not reasons else "QUALITY_SCREEN_FAIL",
        "quality_screen_pass": not reasons,
        "numerical_values_inspected": True,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "trace": relative_path,
        "intake": {
            "manifest_sha256": intake["manifest_sha256"],
            "declaration_sha256": intake["declaration_sha256"],
            "protocol_sha256": intake["protocol_sha256"],
        },
        "columns": {
            "time_s": time_column,
            "pressure_mpa_abs": pressure_column,
            "temperature_degC": temperature_column,
            "mass_flow_g_s": flow_column,
            "transferred_mass_kg": mass_column,
        },
        "observed": {
            "rows": row_count,
            "finite_rows": len(times),
            "missing_required_rows": missing_required,
            "time_start_s": min(times) if times else None,
            "time_end_s": max(times) if times else None,
            "pressure_min_mpa_abs": min(pressures) if pressures else None,
            "pressure_max_mpa_abs": max(pressures) if pressures else None,
            "temperature_min_degC": min(temperatures) if temperatures else None,
            "temperature_max_degC": max(temperatures) if temperatures else None,
        },
        "claim_boundary": "A quality-screen pass is not a model-validation result or an IJHE completion result.",
        "reasons": reasons,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trace", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--declaration", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, default=Path("research/external_hrs_intake_protocol.json"))
    parser.add_argument("--bundle-root", type=Path, default=None)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = validate_trace(
        args.trace, args.manifest, args.declaration, args.protocol, bundle_root=args.bundle_root
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output)
    return 0 if result.get("quality_screen_pass") else 2


if __name__ == "__main__":
    raise SystemExit(main())
