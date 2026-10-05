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

from h2station.controlled_station_replay import TraceMapping, fit_station_boundary


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
        pressure_scale_pa_per_unit=float(value.get("pressure_scale_pa_per_unit", 1.0e6)),
        temperature_scale_k_per_unit=float(value.get("temperature_scale_k_per_unit", 1.0)),
        temperature_offset_k=float(value.get("temperature_offset_k", 273.15)),
        flow_scale_kg_s_per_unit=float(value.get("flow_scale_kg_s_per_unit", 1.0)),
        time_format=value.get("time_format"),
        encoding=str(value.get("encoding", "utf-8-sig")),
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True, help="restricted raw CSV file or directory")
    parser.add_argument("--mapping", type=Path, required=True, help="restricted custodian mapping JSON")
    parser.add_argument("--output", type=Path, required=True, help="aggregate result JSON")
    parser.add_argument("--stride", type=int, default=60)
    parser.add_argument("--max-rows-per-file", type=int, default=250_000)
    args = parser.parse_args()
    summary = fit_station_boundary(
        args.input,
        _mapping(args.mapping),
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
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
