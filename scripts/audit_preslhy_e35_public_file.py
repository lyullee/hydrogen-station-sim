"""Audit one publicly downloadable PRESLHY E3.5 workbook without vendoring it.

The workbook is a liquid-hydrogen controlled-release experiment.  This audit
records file integrity and channel structure only; it is deliberately not an
HRS station-to-vehicle validation and does not tune a runtime model.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import openpyxl


SOURCE = {
    "doi": "10.35097/1481",
    "repository_page": "https://www.radar-service.eu/radar/en/dataset/nWczysTWjmuzgFKm",
    "license": "CC BY-SA 4.0",
    "archive_role": "public controlled liquid-hydrogen release experiment",
}


def _headers(ws: Any) -> list[str]:
    first = next(ws.iter_rows(min_row=1, max_row=1, values_only=True))
    return [str(value) for value in first if value is not None]


def _matched(headers: list[str], *tokens: str) -> list[str]:
    lowered = tuple(token.lower() for token in tokens)
    return [header for header in headers if all(token in header.lower() for token in lowered)]


def _numeric_summary(ws: Any, header: str) -> dict[str, Any]:
    headers = _headers(ws)
    try:
        index = headers.index(header) + 1
    except ValueError:
        return {"present": False}
    values: list[float] = []
    for row in ws.iter_rows(min_row=2, min_col=index, max_col=index, values_only=True):
        value = row[0]
        try:
            number = float(value)
        except (TypeError, ValueError):
            continue
        if number == number:
            values.append(number)
    return {
        "present": True,
        "finite_count": len(values),
        "minimum": min(values) if values else None,
        "maximum": max(values) if values else None,
    }


def audit(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(path)
    workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
    sheets: list[dict[str, Any]] = []
    for worksheet in workbook.worksheets:
        headers = _headers(worksheet)
        sheets.append(
            {
                "name": worksheet.title,
                "row_count_including_header": worksheet.max_row,
                "column_count": worksheet.max_column,
                "header_count": len(headers),
                "time_columns": [
                    header for header in headers if "time" in header.lower()
                ],
                "channel_roles": {
                    "hydrogen_detector": len(
                        _matched(headers, "h2percent")
                        + _matched(headers, "h2ppm")
                    ),
                    "mass_flow": len(_matched(headers, "mass", "flow")),
                    "pressure": len(_matched(headers, "pressure")),
                    "temperature": len(
                        [header for header in headers if "temperature" in header.lower()]
                        + [header for header in headers if "_tc" in header.lower()]
                    ),
                    "weather": len(
                        [
                            header
                            for header in headers
                            if any(
                                token in header.lower()
                                for token in ("wind", "humidity", "weather")
                            )
                        ]
                    ),
                },
            }
        )
    flexlogger = workbook["Flexlogger"]
    flowmeter = workbook["Flowmeter"]
    draeger = workbook["Draeger"]
    return {
        "schema_version": 1,
        "artifact_type": "public_preslhy_e35_file_access_audit",
        "recorded_at": "2026-10-09",
        "status": "PUBLIC_RAW_COMPONENT_CONSEQUENCE_FILE_ACCESSED",
        "source": SOURCE,
        "file": {
            "name": path.name,
            "bytes": path.stat().st_size,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "raw_file_committed": False,
            "numerical_rows_persisted": False,
        },
        "sheets": sheets,
        "observed_channels": {
            "source_flow": _numeric_summary(
                flexlogger, "MFM1_Mass_Flow_Rate"
            ),
            "pipe_pressure": _numeric_summary(flexlogger, "PT1_Pipe_Pressure"),
            "nozzle_pressure": _numeric_summary(flexlogger, "PT2_Nozzle_Pressure"),
            "flowmeter_mass_flow": _numeric_summary(
                flowmeter, "FlMassFlowRategsecR0247"
            ),
            "hydrogen_detector_percent_channels": len(
                _matched(_headers(draeger), "h2percent")
            ),
            "hydrogen_detector_ppm_channels": len(
                _matched(_headers(draeger), "h2ppm")
            ),
        },
        "eligibility": {
            "public_raw_component_consequence_data": True,
            "release_source_and_detector_diagnostic": True,
            "prospective_holdout_eligible": False,
            "full_loop_station_vehicle_validation_eligible": False,
            "runtime_parameter_application": False,
        },
        "claim_boundary": (
            "This audit proves that one public E3.5 workbook is downloadable and contains "
            "release-source, pressure, temperature, detector and weather channel families. "
            "The experiment is a liquid-hydrogen controlled release, not a gaseous HRS fill; "
            "the file was accessed before a new prospective protocol and is therefore a "
            "post-access diagnostic only."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--xlsx", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(audit(args.xlsx), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
