"""Write a privacy-bounded, channel-indexed pressure evidence artifact.

The input path and mapping are restricted custodian inputs.  The generated
JSON contains only generic channel indices and aggregate pressure statistics;
raw rows, filenames, source tags and timestamps are never written.  The
channel-to-bank mapping remains an external attestation and the result is not
automatically applied to model parameters.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from h2station.controlled_station_replay import (
    TraceMapping,
    summarize_pressure_channel_envelopes,
)


def _mapping(path: Path) -> TraceMapping:
    value = json.loads(path.read_text(encoding="utf-8"))
    return TraceMapping(
        time_column=(str(value["time_column"]) if value.get("time_column") else None),
        time_column_index=(
            int(value["time_column_index"])
            if value.get("time_column_index") is not None else None
        ),
        pressure_columns=tuple(
            (str(item[0]), str(item[1]))
            for item in value.get("pressure_columns", [])
        ),
        pressure_scale_pa_per_unit=float(
            value.get("pressure_scale_pa_per_unit", 1.0e6)
        ),
        time_format=value.get("time_format"),
        time_is_absolute=bool(value.get("time_is_absolute", False)),
        encoding=str(value.get("encoding", "utf-8-sig")),
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--mapping", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--stride", type=int, default=600)
    parser.add_argument("--max-rows-per-file", type=int, default=250_000)
    parser.add_argument("--value-cap-per-channel", type=int, default=50_000)
    args = parser.parse_args()

    summaries = summarize_pressure_channel_envelopes(
        args.input,
        _mapping(args.mapping),
        stride=args.stride,
        max_rows_per_file=args.max_rows_per_file,
        value_cap_per_channel=args.value_cap_per_channel,
    )
    result = {
        "schema_version": 1,
        "artifact_type": "confidential_station_boundary_channel_envelopes",
        "recorded_at": "2026-10-06",
        "source_identifiers_published": False,
        "raw_rows_persisted": False,
        "exact_source_dates_published": False,
        "sampling": {
            "stride": args.stride,
            "max_rows_per_file": args.max_rows_per_file,
            "value_cap_per_channel": args.value_cap_per_channel,
        },
        "channels": {
            f"boundary_channel_{index}": summary.to_public_dict()
            for index, summary in enumerate(summaries, start=1)
        },
        "eligibility": {
            "channel_specific_boundary_envelopes_supported": bool(summaries),
            "bank_role_mapping_attested": False,
            "runtime_parameter_application": False,
        },
        "claim_boundary": (
            "De-identified channel-indexed pressure envelopes for station-boundary "
            "plausibility and operator review only; channel-to-bank identity, "
            "vehicle-side accuracy, safety distance and full-loop validation are "
            "not established."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
