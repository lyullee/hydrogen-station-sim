"""Audit the complete public MetHyTrucks sampling-system workbook release.

The measurement values were inspected before this audit was written.  The
result is therefore a post-access data-quality and component-physics
diagnostic.  It is deliberately not a prospective station-to-vehicle
validation result.
"""

from __future__ import annotations

import argparse
from datetime import datetime, time, timezone
import hashlib
import json
from pathlib import Path
from statistics import median
from typing import Any, Iterable

from openpyxl import load_workbook


DATASET_RECORDS = {
    "20590761": "10.5281/zenodo.20590761",
    "20590842": "10.5281/zenodo.20590842",
    "20590903": "10.5281/zenodo.20590903",
}
GUIDE_RECORD = {
    "record_id": "20540258",
    "doi": "10.5281/zenodo.20540258",
}
FLOW_TAG = "QT_D02 ValueY"
MASS_TAG = "FWg35_Masse ValueY"
TANK_PRESSURE_TAG = "PT01 ValueY"
TANK_TEMPERATURE_TAGS = (
    "TT08 ValueY",
    "TT09 ValueY",
    "TT10 ValueY",
    "TT11 ValueY",
)


def _digest(path: Path, algorithm: str) -> str:
    digest = hashlib.new(algorithm)
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _clock_seconds(value: Any) -> float:
    if isinstance(value, (datetime, time)):
        return float(
            value.hour * 3600
            + value.minute * 60
            + value.second
            + value.microsecond / 1.0e6
        )
    if isinstance(value, (int, float)):
        # Excel stores times of day as fractions of a day.  Accept elapsed
        # seconds too so the helper remains useful for synthetic tests.
        return float(value * 86400.0 if 0.0 <= value < 1.0 else value)
    raise ValueError(f"unsupported time value: {value!r}")


def _unwrap_elapsed(values: Iterable[Any]) -> list[float]:
    clock = [_clock_seconds(value) for value in values]
    if not clock:
        return []
    unwrapped = [clock[0]]
    offset = 0.0
    for current, previous in zip(clock[1:], clock):
        if current + offset < unwrapped[-1] and current < previous:
            offset += 86400.0
        unwrapped.append(current + offset)
    origin = unwrapped[0]
    return [value - origin for value in unwrapped]


def _finite_numbers(values: Iterable[Any]) -> list[float]:
    result: list[float] = []
    for value in values:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        number = float(value)
        if number == number and abs(number) != float("inf"):
            result.append(number)
    return result


def _channel_summary(values: list[Any]) -> dict[str, Any]:
    numeric = _finite_numbers(values)
    if not numeric:
        return {
            "numeric_count": 0,
            "missing_or_non_numeric_count": len(values),
        }
    return {
        "numeric_count": len(numeric),
        "missing_or_non_numeric_count": len(values) - len(numeric),
        "first": numeric[0],
        "last": numeric[-1],
        "minimum": min(numeric),
        "maximum": max(numeric),
    }


def _active_sessions(
    elapsed_s: list[float],
    flow: list[float],
    *,
    threshold: float = 1.0,
    join_gap_s: float = 180.0,
) -> list[tuple[int, int]]:
    active = [index for index, value in enumerate(flow) if value > threshold]
    if not active:
        return []
    runs: list[list[int]] = [[active[0], active[0]]]
    for index in active[1:]:
        if index == runs[-1][1] + 1:
            runs[-1][1] = index
        else:
            runs.append([index, index])
    sessions: list[list[int]] = [runs[0]]
    for start, end in runs[1:]:
        if elapsed_s[start] - elapsed_s[sessions[-1][1]] <= join_gap_s:
            sessions[-1][1] = end
        else:
            sessions.append([start, end])
    return [(start, end) for start, end in sessions]


def _trapezoid(values: list[float], times: list[float]) -> float:
    return sum(
        (right_t - left_t) * (left_v + right_v) / 2.0
        for left_v, right_v, left_t, right_t in zip(
            values[:-1], values[1:], times[:-1], times[1:]
        )
    )


def _mass_closure_sessions(
    elapsed_s: list[float], channels: dict[str, list[Any]]
) -> list[dict[str, Any]]:
    if FLOW_TAG not in channels or MASS_TAG not in channels:
        return []
    flow = [float(value) for value in channels[FLOW_TAG]]
    mass = [float(value) for value in channels[MASS_TAG]]
    results: list[dict[str, Any]] = []
    for start, end in _active_sessions(elapsed_s, flow):
        raw_flow = flow[start : end + 1]
        count = min(20, len(raw_flow))
        baseline = median(sorted(raw_flow)[:count])
        corrected_flow = [max(value - baseline, 0.0) for value in raw_flow]
        relative_time = [value - elapsed_s[start] for value in elapsed_s[start : end + 1]]
        integrated_mass_kg = _trapezoid(
            [value / 1000.0 for value in corrected_flow], relative_time
        )
        scale_delta_kg = mass[end] - mass[start]
        ratio = integrated_mass_kg / scale_delta_kg if scale_delta_kg > 0.0 else None
        eligible = bool(
            ratio is not None
            and 0.8 <= ratio <= 1.2
            and integrated_mass_kg >= 0.05
            and relative_time[-1] >= 10.0
        )
        results.append(
            {
                "start_elapsed_s": elapsed_s[start],
                "end_elapsed_s": elapsed_s[end],
                "duration_s": relative_time[-1],
                "flow_baseline_raw_units": baseline,
                "peak_corrected_flow_raw_units": max(corrected_flow),
                "integrated_flow_mass_assuming_g_per_s_kg": integrated_mass_kg,
                "scale_delta_assuming_kg": scale_delta_kg,
                "flow_to_scale_mass_ratio": ratio,
                "descriptive_closure_screen_pass": eligible,
            }
        )
    return results


def summarize_workbook(path: Path) -> dict[str, Any]:
    workbook = load_workbook(path, read_only=True, data_only=True)
    try:
        sheet_names = list(workbook.sheetnames)
        sheet = workbook[sheet_names[0]]
        rows = sheet.iter_rows(values_only=True)
        raw_headers = list(next(rows))
        headers: list[str] = []
        indices: list[int] = []
        for index, value in enumerate(raw_headers):
            if value is None or not str(value).strip():
                continue
            header = str(value).strip()
            if header in headers:
                continue
            headers.append(header)
            indices.append(index)
        records = list(rows)
    finally:
        workbook.close()

    columns = {
        header: [row[index] if index < len(row) else None for row in records]
        for header, index in zip(headers, indices)
    }
    if "Zeit" not in columns:
        raise ValueError(f"{path.name}: Zeit column missing")
    elapsed_s = _unwrap_elapsed(columns["Zeit"])
    intervals = [right - left for left, right in zip(elapsed_s[:-1], elapsed_s[1:])]
    numeric_channels = {
        header: values
        for header, values in columns.items()
        if header != "Zeit" and len(_finite_numbers(values)) == len(values)
    }
    sessions = _mass_closure_sessions(elapsed_s, numeric_channels)
    return {
        "filename": path.name,
        "sha256": _digest(path, "sha256"),
        "sheet_names": sheet_names,
        "sample_count": len(records),
        "duration_s": elapsed_s[-1] if elapsed_s else 0.0,
        "sampling_interval_s": median(intervals) if intervals else None,
        "sampling_interval_max_abs_deviation_s": (
            max(abs(value - median(intervals)) for value in intervals)
            if intervals
            else None
        ),
        "time_monotonic": all(value > 0.0 for value in intervals),
        "headers": headers,
        "channels": {
            header: _channel_summary(values)
            for header, values in numeric_channels.items()
        },
        "has_flow_channel": FLOW_TAG in numeric_channels,
        "has_mass_channel": MASS_TAG in numeric_channels,
        "has_candidate_receiving_cylinder_pressure": TANK_PRESSURE_TAG in numeric_channels,
        "has_four_candidate_receiving_cylinder_temperatures": all(
            tag in numeric_channels for tag in TANK_TEMPERATURE_TAGS
        ),
        "mass_closure_sessions": sessions,
    }


def _metadata_files(metadata: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(item["key"]): item for item in metadata.get("files", [])}


def build_report(data_root: Path, *, recorded_date: str) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    all_workbooks: list[dict[str, Any]] = []
    integrity_errors: list[str] = []

    for record_id, expected_doi in DATASET_RECORDS.items():
        record_dir = data_root / record_id
        metadata_path = record_dir / "metadata.json"
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        files = _metadata_files(metadata)
        workbook_entries: list[dict[str, Any]] = []
        for filename, entry in sorted(files.items()):
            if not filename.lower().endswith(".xlsx"):
                continue
            path = record_dir / filename
            if not path.is_file():
                integrity_errors.append(f"missing file: {record_id}/{filename}")
                continue
            expected_checksum = str(entry.get("checksum", ""))
            observed_md5 = _digest(path, "md5")
            if expected_checksum != f"md5:{observed_md5}":
                integrity_errors.append(f"MD5 mismatch: {record_id}/{filename}")
            if int(entry.get("size", -1)) != path.stat().st_size:
                integrity_errors.append(f"size mismatch: {record_id}/{filename}")
            summary = summarize_workbook(path)
            summary.update(
                {
                    "record_id": record_id,
                    "zenodo_md5": expected_checksum,
                    "byte_size": path.stat().st_size,
                }
            )
            workbook_entries.append(summary)
            all_workbooks.append(summary)
        doi = str(metadata.get("doi") or metadata.get("metadata", {}).get("doi") or "")
        if doi != expected_doi:
            integrity_errors.append(f"DOI mismatch: {record_id}: {doi}")
        records.append(
            {
                "record_id": record_id,
                "doi": doi,
                "title": metadata.get("title") or metadata.get("metadata", {}).get("title"),
                "license": (metadata.get("metadata", {}).get("license") or {}).get("id"),
                "metadata_sha256": _digest(metadata_path, "sha256"),
                "workbook_count": len(workbook_entries),
                "workbooks": workbook_entries,
            }
        )

    guide_dir = data_root / GUIDE_RECORD["record_id"]
    guide_metadata_path = guide_dir / "metadata.json"
    guide_metadata = json.loads(guide_metadata_path.read_text(encoding="utf-8"))
    guide_files = _metadata_files(guide_metadata)
    guide_entry = next(iter(guide_files.values()))
    guide_path = guide_dir / str(guide_entry["key"])
    guide_md5 = _digest(guide_path, "md5")
    if str(guide_entry.get("checksum")) != f"md5:{guide_md5}":
        integrity_errors.append("D1 guide MD5 mismatch")

    common_headers = sorted(
        set.intersection(*(set(item["headers"]) for item in all_workbooks))
    )
    closure_sessions = [
        {"record_id": workbook["record_id"], "filename": workbook["filename"], **session}
        for workbook in all_workbooks
        for session in workbook["mass_closure_sessions"]
    ]
    closure_comparable = [
        item
        for item in closure_sessions
        if item["flow_to_scale_mass_ratio"] is not None
    ]
    closure_passes = [
        item for item in closure_comparable if item["descriptive_closure_screen_pass"]
    ]
    closure_ratios = [
        float(item["flow_to_scale_mass_ratio"])
        for item in closure_passes
        if item["flow_to_scale_mass_ratio"] is not None
    ]
    closure_comparable_ratios = [
        float(item["flow_to_scale_mass_ratio"])
        for item in closure_comparable
    ]
    closure_absolute_relative_differences_pct = [
        abs(value - 1.0) * 100.0 for value in closure_comparable_ratios
    ]
    return {
        "schema_version": 1,
        "recorded_date": recorded_date,
        "status": "PASS" if not integrity_errors else "FAIL",
        "evidence_role": "post_access_public_measurement_intake_and_component_diagnostic",
        "sources": {
            "measurement_records": records,
            "good_practice_guide": {
                "record_id": GUIDE_RECORD["record_id"],
                "doi": GUIDE_RECORD["doi"],
                "title": guide_metadata.get("title")
                or guide_metadata.get("metadata", {}).get("title"),
                "license": (guide_metadata.get("metadata", {}).get("license") or {}).get("id"),
                "file": str(guide_entry["key"]),
                "zenodo_md5": guide_entry.get("checksum"),
                "observed_md5": f"md5:{guide_md5}",
                "byte_size": guide_path.stat().st_size,
            },
        },
        "integrity": {
            "all_zenodo_md5_and_sizes_match": not integrity_errors,
            "errors": integrity_errors,
            "raw_files_committed": False,
            "raw_location": "gitignored tmp/methytrucks_2026",
        },
        "aggregate": {
            "record_count": len(records),
            "workbook_count": len(all_workbooks),
            "sample_count": sum(item["sample_count"] for item in all_workbooks),
            "all_time_axes_monotonic": all(item["time_monotonic"] for item in all_workbooks),
            "sampling_intervals_s": sorted(
                {item["sampling_interval_s"] for item in all_workbooks}
            ),
            "common_headers": common_headers,
            "workbooks_with_flow": sum(item["has_flow_channel"] for item in all_workbooks),
            "workbooks_with_mass": sum(item["has_mass_channel"] for item in all_workbooks),
            "workbooks_with_receiving_cylinder_pressure_and_four_temperatures": sum(
                item["has_candidate_receiving_cylinder_pressure"]
                and item["has_four_candidate_receiving_cylinder_temperatures"]
                for item in all_workbooks
            ),
            "mass_closure_session_count": len(closure_sessions),
            "mass_closure_comparable_session_count": len(closure_comparable),
            "mass_closure_non_comparable_session_count": (
                len(closure_sessions) - len(closure_comparable)
            ),
            "mass_closure_screen_pass_count": len(closure_passes),
            "mass_closure_comparable_pass_fraction": (
                len(closure_passes) / len(closure_comparable)
                if closure_comparable
                else None
            ),
            "mass_closure_pass_ratio_median": median(closure_ratios)
            if closure_ratios
            else None,
            "mass_closure_comparable_ratio_median": (
                median(closure_comparable_ratios)
                if closure_comparable_ratios
                else None
            ),
            "mass_closure_comparable_absolute_relative_difference_pct_median": (
                median(closure_absolute_relative_differences_pct)
                if closure_absolute_relative_differences_pct
                else None
            ),
        },
        "mass_closure_sessions": closure_sessions,
        "eligibility": {
            "public_real_experimental_measurements": True,
            "synchronized_component_trace_candidate": True,
            "flow_mass_consistency_diagnostic_supported": bool(closure_passes),
            "receiving_cylinder_thermal_diagnostic_candidate": any(
                item["has_candidate_receiving_cylinder_pressure"]
                and item["has_four_candidate_receiving_cylinder_temperatures"]
                for item in all_workbooks
            ),
            "prospective_holdout_eligible": False,
            "full_loop_station_vehicle_validation_eligible": False,
        },
        "mapping_boundary": {
            "publisher_channel_dictionary_present": False,
            "engineering_units_in_workbook_headers": False,
            "workbook_to_sampling_device_crosswalk_present": False,
            "vehicle_identity_and_tank_geometry_present": False,
            "station_controller_bank_valve_states_present": False,
            "sensor_calibration_uncertainty_present": False,
            "guide_use": (
                "D1 supplies operating-practice context but does not define the logger tags, "
                "workbook-to-device mapping, sensor units or controller states."
            ),
        },
        "claim_boundary": (
            "The 15 CC BY 4.0 workbooks are real public experimental traces and can support "
            "post-access component diagnostics, including descriptive flow-to-scale mass "
            "closure. Outcomes were inspected before this audit and the release lacks an "
            "authoritative tag/unit dictionary, device crosswalk, vehicle geometry and station "
            "controller states. It therefore does not establish prospective validation, a "
            "complete HRS-to-vehicle full-loop result, safety performance or regulatory compliance."
        ),
    }


def render_markdown(report: dict[str, Any]) -> str:
    aggregate = report["aggregate"]
    lines = [
        "# MetHyTrucks 2026 public measurement intake",
        "",
        "This audit covers all three public sampling-system releases available from the",
        "MetHyTrucks Zenodo community. Raw workbooks remain outside version control.",
        "",
        "## Result",
        "",
        f"- Integrity status: **{report['status']}**",
        f"- Public records: **{aggregate['record_count']}**",
        f"- Workbooks: **{aggregate['workbook_count']}**",
        f"- Synchronized samples: **{aggregate['sample_count']:,}**",
        f"- Sampling interval(s): **{', '.join(str(v) for v in aggregate['sampling_intervals_s'])} s**",
        f"- Workbooks with a mass channel: **{aggregate['workbooks_with_mass']}**",
        f"- Detected transfer sessions: **{aggregate['mass_closure_session_count']}**",
        f"- Sessions with a non-zero scale change and therefore eligible for closure comparison: **{aggregate['mass_closure_comparable_session_count']}**",
        f"- Descriptive flow/mass closure screens passed: **{aggregate['mass_closure_screen_pass_count']} / {aggregate['mass_closure_comparable_session_count']} comparable sessions**",
        f"- Sessions without a measurable scale change (not scored): **{aggregate['mass_closure_non_comparable_session_count']}**",
        f"- Median flow/scale ratio across comparable sessions: **{aggregate['mass_closure_comparable_ratio_median']:.3f}**",
        f"- Median absolute relative flow/scale difference: **{aggregate['mass_closure_comparable_absolute_relative_difference_pct_median']:.2f}%**",
        "",
        "## Source records",
        "",
        "| Group | DOI | Workbooks | License |",
        "|---|---|---:|---|",
    ]
    for source in report["sources"]["measurement_records"]:
        lines.append(
            f"| {source['title']} | [{source['doi']}](https://doi.org/{source['doi']}) | "
            f"{source['workbook_count']} | {source['license']} |"
        )
    guide = report["sources"]["good_practice_guide"]
    lines.extend(
        [
            "",
            "The operating-context check used the public",
            f"[{guide['title']}](https://doi.org/{guide['doi']}).",
            "",
            "## Scientific use",
            "",
            "The archive materially strengthens provenance for real HRS sampling-system",
            "pressure, temperature, flow and transferred-mass behavior. The flow/mass",
            "closure calculation is a post-access component diagnostic and records every",
            "passing and failing session.",
            "",
            "It does not close the station-to-vehicle full-loop gate. The release does not",
            "contain an authoritative channel/unit dictionary, an explicit workbook-to-device",
            "crosswalk, vehicle tank geometry, controller/bank/valve states or calibration",
            "uncertainties. D1 provides operating guidance but does not fill those metadata gaps.",
            "",
            "## Claim boundary",
            "",
            report["claim_boundary"],
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, default=Path("tmp/methytrucks_2026"))
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("research/methytrucks_2026_public_measurement_intake.json"),
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        default=Path("research/METHYTRUCKS_2026_PUBLIC_MEASUREMENT_INTAKE.md"),
    )
    parser.add_argument(
        "--recorded-date", default=datetime.now(timezone.utc).date().isoformat()
    )
    args = parser.parse_args()
    report = build_report(args.data_root, recorded_date=args.recorded_date)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    args.markdown_output.write_text(
        render_markdown(report), encoding="utf-8", newline="\n"
    )
    print(json.dumps(report["aggregate"], ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
