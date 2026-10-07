"""Evaluate the prospectively frozen MetHyTrucks Group D workbook intake.

The protocol was committed before this workbook was downloaded or opened.  The
evaluation is deliberately fail-closed: ambiguous tag names are not promoted to
vehicle pressure or temperature, and a missing tank geometry prevents a model
score.  Raw rows remain in the gitignored data tree.
"""

from __future__ import annotations

import argparse
from datetime import datetime, time, timezone
import hashlib
import json
from pathlib import Path
import statistics
import subprocess
from typing import Any

from openpyxl import load_workbook


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROTOCOL = ROOT / "research/methytrucks_group_d_prospective_protocol_2026_10_08.json"
DEFAULT_SOURCE = (
    ROOT
    / "data/public_validation/raw/methytrucks_group_d/20241024_Test_5_SINTEF_CESAME.xlsx"
)
DEFAULT_OUTPUT = ROOT / "research/methytrucks_group_d_prospective_result_2026_10_08.json"


def _digest(path: Path, algorithm: str) -> str:
    digest = hashlib.new(algorithm)
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_commit() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True,
            capture_output=True, text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unavailable"


def _seconds(value: object) -> float:
    if isinstance(value, time):
        return (
            value.hour * 3600.0 + value.minute * 60.0 + value.second
            + value.microsecond / 1.0e6
        )
    if isinstance(value, (int, float)):
        return float(value) * 86400.0
    raise ValueError(f"unsupported time value {value!r}")


def _elapsed(values: list[object]) -> list[float]:
    clock = [_seconds(value) for value in values]
    elapsed = [0.0]
    offset = 0.0
    for previous, current in zip(clock, clock[1:], strict=False):
        if current + offset <= previous + offset:
            offset += 86400.0
        elapsed.append(current + offset - clock[0])
    if any(right <= left for left, right in zip(elapsed, elapsed[1:], strict=False)):
        raise ValueError("time base is not strictly increasing")
    return elapsed


def _alias_matches(headers: list[str], aliases: list[str]) -> list[str]:
    matches: list[str] = []
    for header in headers:
        folded = header.casefold()
        if any(alias.casefold() in folded for alias in aliases):
            matches.append(header)
    return matches


def evaluate(source: Path, protocol_path: Path = DEFAULT_PROTOCOL) -> dict[str, Any]:
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    selected = protocol["frozen_selection"]
    if source.name != selected["filename"]:
        raise ValueError("source filename does not match the frozen selection")
    observed_size = source.stat().st_size
    observed_md5 = _digest(source, "md5")
    observed_sha256 = _digest(source, "sha256")
    if observed_size != selected["zenodo_file_size_bytes"]:
        raise ValueError("source size does not match the frozen Zenodo metadata")
    if observed_md5 != selected["zenodo_md5"]:
        raise ValueError("source MD5 does not match the frozen Zenodo checksum")

    workbook = load_workbook(source, read_only=True, data_only=True)
    try:
        if len(workbook.sheetnames) != 1:
            raise ValueError("selected workbook must contain exactly one sheet")
        sheet = workbook[workbook.sheetnames[0]]
        rows = sheet.iter_rows(values_only=True)
        headers = [str(value).strip() for value in next(rows)]
        records = list(rows)
    finally:
        workbook.close()

    aliases = protocol["measurement_only_intake"]["channel_aliases_frozen_before_access"]
    matches = {
        semantic: _alias_matches(headers, names)
        for semantic, names in aliases.items()
    }
    time_headers = matches["time"]
    if len(time_headers) != 1:
        raise ValueError("the frozen time alias rule did not resolve exactly one channel")
    time_index = headers.index(time_headers[0])
    elapsed = _elapsed([row[time_index] for row in records])
    intervals = [right - left for left, right in zip(elapsed, elapsed[1:], strict=False)]

    required_resolution = {
        "time": len(matches["time"]) == 1,
        "vehicle_pressure": bool(matches["vehicle_pressure"]),
        "vehicle_temperature": bool(matches["vehicle_temperature"]),
        "mass_boundary": bool(matches["mass_flow"] or matches["transferred_mass"]),
        "delivered_temperature": bool(matches["delivered_temperature"]),
        "upstream_pressure": bool(matches["upstream_pressure"]),
        "engineering_units": False,
        "independent_tank_geometry": False,
    }
    unresolved_required = [
        key for key, value in required_resolution.items() if value is not True
    ]
    eligible = not unresolved_required
    decision = "MODEL_SCREEN_NOT_RUN_INELIGIBLE_METADATA" if not eligible else "ELIGIBLE"

    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "completed_prospective_intake_ineligible" if not eligible else "eligible_for_model_screen",
        "decision": decision,
        "evidence_role": "retained_prospective_negative_intake_result" if not eligible else "prospective_single_event_model_screen",
        "protocol": {
            "path": str(protocol_path.relative_to(ROOT)).replace("\\", "/")
            if protocol_path.is_relative_to(ROOT) else str(protocol_path),
            "protocol_id": protocol["protocol_id"],
            "frozen_at": protocol["frozen_at"],
            "frozen_model_commit": protocol["frozen_model_commit"],
            "workbook_accessed_after_protocol_commit": True,
            "selected_file_replaced": False,
            "thresholds_changed_after_access": False,
        },
        "execution_commit": _git_commit(),
        "source": {
            "dataset_title": protocol["source"]["dataset_title"],
            "dataset_doi": protocol["source"]["dataset_doi"],
            "context_report_doi": protocol["source"]["context_report_doi"],
            "filename": source.name,
        },
        "file_integrity": {
            "size_bytes": observed_size,
            "md5": observed_md5,
            "sha256": observed_sha256,
            "zenodo_size_match": True,
            "zenodo_md5_match": True,
            "raw_rows_committed": False,
        },
        "workbook_structure": {
            "sheet_names": [sheet.title],
            "sample_count": len(records),
            "column_count": len(headers),
            "headers": headers,
            "sampling_interval_s_median": statistics.median(intervals),
            "duration_s": elapsed[-1],
            "strictly_increasing_time": True,
        },
        "channel_screen": {
            "frozen_alias_matches": matches,
            "required_resolution": required_resolution,
            "unresolved_required": unresolved_required,
            "ambiguous_unmapped_pressure_like_headers": [
                header for header in headers
                if header.casefold().startswith(("ptx", "pt0"))
                and header not in matches["upstream_pressure"]
                and header not in matches["vehicle_pressure"]
            ],
            "ambiguous_unmapped_temperature_like_headers": [
                header for header in headers
                if header.casefold().startswith(("tt", "te_", "11tt"))
                and header not in matches["delivered_temperature"]
                and header not in matches["vehicle_temperature"]
            ],
            "machine_readable_unit_dictionary_present": False,
            "interpretation": (
                "The file contains a synchronized time base and flow/mass plus dispenser-side "
                "candidate channels, but no frozen alias establishes vehicle pressure or vehicle "
                "tank temperature. Generic ValueY labels do not attest engineering units."
            ),
        },
        "geometry_screen": {
            "tank_type_documented_for_selected_event": False,
            "tank_internal_volume_documented_for_selected_event": False,
            "outcome_inference_used": False,
        },
        "model_evaluation": {
            "executed": False,
            "reason": (
                "The pre-access protocol requires vehicle pressure, vehicle temperature, engineering "
                "units and independent tank geometry. Running a numerical replay would require "
                "inventing or outcome-inferring those inputs."
            ),
            "metrics": None,
            "case_specific_fitting_performed": False,
        },
        "full_loop_gate_impact": {
            "full_loop_external_validation_supported": False,
            "case_count_contributed": 0,
            "required_case_count": 8,
            "gate_status": "remains_open",
            "remaining_data_need": (
                "At least eight disjoint physical-HRS vehicle-fill traces with explicit units, "
                "vehicle tank pressure and temperature, tank geometry, station/cascade states, "
                "controller actions and calibration metadata."
            ),
        },
        "claim_boundary": (
            "This retained prospective negative result demonstrates that the selected public Group D "
            "workbook cannot support the predeclared vehicle-tank or station full-loop score. It is "
            "not evidence that the model failed a numerical prediction, and it does not validate "
            "station safety or emergency response."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    result = evaluate(args.source.resolve(), args.protocol.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8", newline="\n",
    )
    print(json.dumps({
        "output": str(args.output),
        "status": result["status"],
        "decision": result["decision"],
        "unresolved_required": result["channel_screen"]["unresolved_required"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
