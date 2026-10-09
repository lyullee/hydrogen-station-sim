"""Export a small, de-identified HRS component-evidence bundle.

This is the low-burden intake path described in
``research/full_loop_raw_data_request_package_2026_10_05.json``.  It accepts
three or more custodian-controlled event CSVs containing the station/dispenser
boundary channels, normalizes time to zero for each event, and writes the
generic result only outside the Git worktree.  It is deliberately weaker than
the full-loop exporter: the output can support component replay and operating-
range checks, but never claims station-to-vehicle validation, safety distance,
or SAGA effectiveness.
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_CANONICAL_COLUMNS = (
    "time_s",
    "station_pressure_mpa_abs",
    "boundary_temperature_degC",
    "mass_flow_g_s",
    "protocol_phase",
)
NUMERIC_COLUMNS = (
    "station_pressure_mpa_abs",
    "boundary_temperature_degC",
    "mass_flow_g_s",
)
OUTPUT_COLUMNS = REQUIRED_CANONICAL_COLUMNS
EXPECTED_UNITS = {
    "station_pressure_mpa_abs": "MPa_abs",
    "boundary_temperature_degC": "degC",
    "mass_flow_g_s": "g/s",
}


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _outside_repository(path: Path, *, field: str) -> Path:
    resolved = path.expanduser().resolve()
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError:
        return resolved
    raise ValueError(f"{field} must be outside the repository worktree")


def _finite(value: object, *, column: str, row_number: int) -> float:
    try:
        number = float(value.strip()) if isinstance(value, str) else float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"row {row_number}: {column} is not numeric") from exc
    if not math.isfinite(number):
        raise ValueError(f"row {row_number}: {column} is not finite")
    return number


def _time_seconds(value: object, *, mapping: dict[str, Any], row_number: int) -> float:
    raw = value.strip() if isinstance(value, str) else "" if value is None else str(value).strip()
    if not raw:
        raise ValueError(f"row {row_number}: time is empty")
    time_format = mapping.get("time_format")
    if time_format:
        try:
            return datetime.strptime(raw, str(time_format)).replace(tzinfo=timezone.utc).timestamp()
        except ValueError as exc:
            raise ValueError(f"row {row_number}: time does not match time_format") from exc
    try:
        return _finite(raw, column="time", row_number=row_number)
    except ValueError as numeric_error:
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00")).timestamp()
        except ValueError:
            raise numeric_error


def _validate_contract(mapping: dict[str, Any], attestation: dict[str, Any], protocol: dict[str, Any]) -> None:
    if mapping.get("schema_version") != 1:
        raise ValueError("mapping schema_version must be 1")
    if attestation.get("schema_version") != 1:
        raise ValueError("attestation schema_version must be 1")
    if attestation.get("authorised_controlled_evaluation") is not True:
        raise ValueError("attestation must authorize controlled evaluation")
    if attestation.get("outcomes_accessed_before_protocol_freeze") is not False:
        raise ValueError("attestation must confirm pre-outcome freeze")
    if protocol.get("status") != "prospective_component_intake_contract":
        raise ValueError("protocol is not a prospective component intake contract")
    if protocol.get("outcomes_accessed_before_freeze") is not False:
        raise ValueError("protocol must prohibit pre-freeze outcome access")
    column_map = mapping.get("column_map")
    if not isinstance(column_map, dict):
        raise ValueError("mapping must contain a column_map object")
    for canonical in REQUIRED_CANONICAL_COLUMNS:
        source = column_map.get(canonical)
        if not isinstance(source, str) or not source.strip():
            raise ValueError(f"mapping is missing source column for {canonical}")
    units = attestation.get("units")
    if not isinstance(units, dict):
        raise ValueError("attestation must contain units")
    for canonical, expected in EXPECTED_UNITS.items():
        if units.get(canonical) != expected:
            raise ValueError(f"attestation unit for {canonical} must be {expected}")


def _read_event(path: Path, mapping: dict[str, Any]) -> tuple[list[dict[str, str]], dict[str, Any]]:
    column_map = mapping["column_map"]
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        header = tuple(reader.fieldnames or ())
        missing = [
            canonical for canonical in REQUIRED_CANONICAL_COLUMNS
            if column_map[canonical] not in header
        ]
        if missing:
            raise ValueError(f"{path.name}: missing mapped channels: {', '.join(missing)}")
        normalized: list[dict[str, str]] = []
        origin: float | None = None
        previous: float | None = None
        for row_number, row in enumerate(reader, start=2):
            absolute_time = _time_seconds(row.get(column_map["time_s"]), mapping=mapping, row_number=row_number)
            if origin is None:
                origin = absolute_time
            time_s = absolute_time - origin
            if previous is not None and time_s <= previous:
                raise ValueError(f"{path.name} row {row_number}: time must be strictly increasing")
            previous = time_s
            phase = str(row.get(column_map["protocol_phase"]) or "").strip()
            if not phase:
                raise ValueError(f"{path.name} row {row_number}: protocol_phase is empty")
            exported = {"time_s": f"{time_s:.9g}"}
            for canonical in NUMERIC_COLUMNS:
                exported[canonical] = f"{_finite(row.get(column_map[canonical]), column=canonical, row_number=row_number):.9g}"
            exported["protocol_phase"] = phase
            normalized.append(exported)
    if len(normalized) < 20:
        raise ValueError(f"{path.name}: component event has fewer than 20 rows")
    return normalized, {
        "rows": len(normalized),
        "duration_s": float(normalized[-1]["time_s"]),
        "min_pressure_mpa_abs": min(float(row["station_pressure_mpa_abs"]) for row in normalized),
        "max_pressure_mpa_abs": max(float(row["station_pressure_mpa_abs"]) for row in normalized),
        "max_mass_flow_g_s": max(float(row["mass_flow_g_s"]) for row in normalized),
    }


def export_component_bundle(
    input_paths: list[Path],
    mapping_path: Path,
    attestation_path: Path,
    output_directory: Path,
    protocol_path: Path,
) -> dict[str, Any]:
    """Normalize a small component bundle without publishing raw source identity."""

    if len(input_paths) < 3:
        raise ValueError("minimum useful component bundle requires at least 3 events")
    inputs = [_outside_repository(path, field="input data") for path in input_paths]
    mapping_path = _outside_repository(mapping_path, field="mapping")
    attestation_path = _outside_repository(attestation_path, field="attestation")
    output_directory = _outside_repository(output_directory, field="output directory")
    protocol_path = protocol_path.expanduser().resolve()
    for path in inputs:
        if not path.is_file():
            raise FileNotFoundError(path)
    mapping = _json(mapping_path)
    attestation = _json(attestation_path)
    protocol = _json(protocol_path)
    _validate_contract(mapping, attestation, protocol)
    if output_directory.exists() and any(output_directory.iterdir()):
        raise ValueError("output directory must be empty")
    output_directory.mkdir(parents=True, exist_ok=True)

    summaries: list[dict[str, Any]] = []
    for index, path in enumerate(inputs, start=1):
        rows, summary = _read_event(path, mapping)
        trace_path = output_directory / f"component_event_{index:03d}.csv"
        with trace_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=OUTPUT_COLUMNS)
            writer.writeheader()
            writer.writerows(rows)
        summaries.append(summary)

    receipt = {
        "schema_version": 1,
        "artifact_type": "controlled_deidentified_hrs_component_bundle_receipt",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "event_count": len(inputs),
        "component_bundle_ready": True,
        "event_summaries": summaries,
        "source_input_sha256": [_sha256(path) for path in inputs],
        "mapping_sha256": _sha256(mapping_path),
        "attestation_sha256": _sha256(attestation_path),
        "protocol_sha256": _sha256(protocol_path),
        "raw_rows_persisted_in_repository": False,
        "runtime_parameter_application": False,
        "full_loop_holdout_eligible": False,
        "claim_boundary": (
            "This controlled component bundle supports station-to-dispenser boundary replay, "
            "operating-range and protocol face-validity checks, and channel-quality screening. "
            "It is not full station-to-vehicle validation, safety-distance evidence, SAGA "
            "effectiveness evidence, or an IJHE completion result."
        ),
    }
    (output_directory / "receipt.json").write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", dest="inputs", action="append", required=True, help="One authorised event CSV; repeat at least three times")
    parser.add_argument("--mapping", type=Path, required=True)
    parser.add_argument("--attestation", type=Path, required=True)
    parser.add_argument("--output-directory", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, default=ROOT / "research/external_hrs_component_intake_protocol.json")
    args = parser.parse_args()
    receipt = export_component_bundle(
        [Path(value) for value in args.inputs], args.mapping, args.attestation,
        args.output_directory, args.protocol,
    )
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
