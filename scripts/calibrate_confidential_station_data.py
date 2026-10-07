"""Calibrate station-boundary aggregates from an owner-controlled CSV bundle.

The raw path and mapping are runtime inputs.  The generated JSON contains
only de-identified aggregate calibration parameters and can be reviewed before
being copied into a public research artifact.  Never point this command at a
public repository checkout containing the raw files.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from h2station.controlled_station_replay import (
    TraceMapping,
    fit_station_boundary,
    summarize_lifecycle_counters,
    synchronize_station_traces,
)
from h2station.restricted_attestation import load_restricted_channel_attestation


def _mapping(path: Path) -> TraceMapping:
    value = json.loads(path.read_text(encoding="utf-8"))
    return TraceMapping(
        time_column=(str(value["time_column"]) if value.get("time_column") else None),
        time_column_index=(int(value["time_column_index"]) if value.get("time_column_index") is not None else None),
        pressure_columns=tuple(
            (str(item[0]), str(item[1])) for item in value.get("pressure_columns", [])
        ),
        temperature_columns=tuple(
            (str(item[0]), str(item[1])) for item in value.get("temperature_columns", [])
        ),
        flow_column=(str(value["flow_column"]) if value.get("flow_column") else None),
        state_columns=tuple(
            (str(item[0]), str(item[1])) for item in value.get("state_columns", [])
        ),
        lifecycle_columns=tuple(
            (str(item[0]), str(item[1])) for item in value.get("lifecycle_columns", [])
        ),
        temperature_boundary_role=(
            str(value["temperature_boundary_role"])
            if value.get("temperature_boundary_role") is not None else None
        ),
        authorized_boundary_roles=tuple(
            str(role) for role in value.get(
                "authorized_boundary_roles", ["station_pressure"]
            )
        ),
        pressure_scale_pa_per_unit=float(value.get("pressure_scale_pa_per_unit", 1.0e6)),
        temperature_scale_k_per_unit=float(value.get("temperature_scale_k_per_unit", 1.0)),
        temperature_offset_k=float(value.get("temperature_offset_k", 273.15)),
        flow_scale_kg_s_per_unit=float(value.get("flow_scale_kg_s_per_unit", 1.0)),
        lifecycle_scale_per_unit=float(value.get("lifecycle_scale_per_unit", 1.0)),
        time_format=value.get("time_format"),
        time_is_absolute=bool(value.get("time_is_absolute", False)),
        encoding=str(value.get("encoding", "utf-8-sig")),
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True, help="restricted raw CSV file or directory")
    parser.add_argument("--mapping", type=Path, required=True, help="restricted custodian mapping JSON")
    parser.add_argument("--output", type=Path, required=True, help="aggregate result JSON")
    parser.add_argument(
        "--attestation", type=Path,
        help=(
            "restricted generic-role/unit attestation; without it the output "
            "remains diagnostic-only and cannot be promoted to a runtime profile"
        ),
    )
    parser.add_argument("--stride", type=int, default=60)
    parser.add_argument("--max-rows-per-file", type=int, default=250_000)
    parser.add_argument(
        "--equipment-input",
        type=Path,
        help="optional restricted equipment logger for an absolute-time overlap check",
    )
    parser.add_argument(
        "--equipment-mapping",
        type=Path,
        help="mapping for --equipment-input",
    )
    parser.add_argument(
        "--lifecycle-input",
        type=Path,
        help="optional restricted lifecycle-counter logger",
    )
    parser.add_argument(
        "--lifecycle-mapping",
        type=Path,
        help="mapping for --lifecycle-input",
    )
    parser.add_argument("--max-match-gap-s", type=float, default=2.0)
    args = parser.parse_args()
    if bool(args.equipment_input) != bool(args.equipment_mapping):
        parser.error("--equipment-input and --equipment-mapping must be supplied together")
    if bool(args.lifecycle_input) != bool(args.lifecycle_mapping):
        parser.error("--lifecycle-input and --lifecycle-mapping must be supplied together")
    mapping = _mapping(args.mapping)
    attestation = (
        load_restricted_channel_attestation(args.attestation, mapping)
        if args.attestation is not None else None
    )
    summary = fit_station_boundary(
        args.input,
        mapping,
        stride=args.stride,
        max_rows_per_file=args.max_rows_per_file,
    )
    result = {
        "schema_version": 1,
        "artifact_type": "confidential_station_boundary_calibration",
        "source_identifiers_published": False,
        "raw_rows_persisted": False,
        "sampling": {
            "stride": args.stride,
            "max_rows_per_file": args.max_rows_per_file,
        },
        "calibration": summary.to_public_dict(),
        "channel_attestation": (
            attestation.to_public_dict()
            if attestation is not None else {
                "provided": False,
                "eligibility": {
                    "station_boundary_calibration_supported": False,
                    "temperature_boundary_supported": False,
                    "recharge_state_calibration_supported": False,
                    "full_station_vehicle_validation": False,
                    "full_loop_holdout_eligible": False,
                },
                "claim_boundary": (
                    "No custodian role/unit attestation was supplied; this "
                    "aggregate is diagnostic-only."
                ),
            }
        ),
    }
    if args.equipment_input:
        alignment = synchronize_station_traces(
            args.input,
            mapping,
            args.equipment_input,
            _mapping(args.equipment_mapping),
            stride=args.stride,
            max_rows=args.max_rows_per_file,
            max_match_gap_s=args.max_match_gap_s,
        )
        result["synchronized_alignment"] = alignment.alignment.to_public_dict()
        result["synchronized_alignment"]["max_match_gap_s"] = args.max_match_gap_s
    if args.lifecycle_input:
        result["lifecycle"] = summarize_lifecycle_counters(
            args.lifecycle_input,
            _mapping(args.lifecycle_mapping),
            stride=args.stride,
            max_rows_per_file=args.max_rows_per_file,
        ).to_public_dict()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
