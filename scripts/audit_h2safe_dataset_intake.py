from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _finite(value: str) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _sensor_count(path: Path) -> int:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        return sum(1 for row in csv.DictReader(stream) if row.get("id"))


def _test_summary(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)
    if "time" not in fieldnames or not rows:
        raise ValueError(f"Missing time series in {path}")
    times = [_finite(row.get("time", "")) for row in rows]
    clean_times = [value for value in times if value is not None]
    if len(clean_times) < 2:
        raise ValueError(f"Insufficient finite timestamps in {path}")
    positive_steps = [
        right - left
        for left, right in zip(clean_times, clean_times[1:])
        if right > left
    ]
    channels = [name for name in fieldnames if name != "time"]
    finite_counts = {
        channel: sum(
            _finite(row.get(channel, "")) is not None
            for row in rows
        )
        for channel in channels
    }
    return {
        "file": path.name,
        "sha256": _sha256(path),
        "row_count": len(rows),
        "time_start_s": min(clean_times),
        "time_end_s": max(clean_times),
        "median_sample_interval_s": statistics.median(positive_steps),
        "declared_channel_count": len(channels),
        "channels_with_any_finite_value": sum(
            count > 0 for count in finite_counts.values()
        ),
        "permanently_missing_channel_count": sum(
            count == 0 for count in finite_counts.values()
        ),
        "missing_cell_count": sum(
            len(rows) - count for count in finite_counts.values()
        ),
    }


def audit(raw_dir: Path) -> dict[str, Any]:
    archive = raw_dir / "Dataset.zip"
    readme = raw_dir / "HVAC_information.docx"
    extracted = raw_dir / "extracted"
    protocol = ROOT / "research/h2safe_helium_detector_protocol_2026_10_08.json"
    if not archive.is_file() or not readme.is_file() or not extracted.is_dir():
        raise FileNotFoundError("H2SAFE archive, README and extracted directory are required")

    labs: list[dict[str, Any]] = []
    for lab_dir in sorted(path for path in extracted.iterdir() if path.is_dir()):
        sensors = lab_dir / "sensors.csv"
        tests = sorted(lab_dir.glob("test*.csv"))
        labs.append({
            "lab_id": lab_dir.name,
            "sensor_coordinate_file": sensors.name,
            "sensor_coordinate_sha256": _sha256(sensors),
            "coordinate_sensor_count": _sensor_count(sensors),
            "test_count": len(tests),
            "tests": [_test_summary(path) for path in tests],
        })

    all_tests = [test for lab in labs for test in lab["tests"]]
    return {
        "schema_version": 1,
        "artifact_type": "public_h2safe_helium_dataset_intake_audit",
        "recorded_at": "2026-10-08",
        "source": {
            "title": "Dataset for H2SAFE - Controlled Gas Releases and Sensor-Response for Indoor Hydrogen Safety",
            "doi": "10.7799/17118570",
            "landing_page": "https://data.nlr.gov/submissions/330",
            "test_gas": "helium",
            "publisher": "National Laboratory of the Rockies",
            "license_page": "https://data.nlr.gov/node/330/license",
        },
        "frozen_protocol": {
            "artifact": "research/h2safe_helium_detector_protocol_2026_10_08.json",
            "sha256": _sha256(protocol),
            "git_commit_before_raw_access": "2ed653b",
        },
        "download": {
            "archive_bytes": archive.stat().st_size,
            "archive_sha256": _sha256(archive),
            "readme_bytes": readme.stat().st_size,
            "readme_sha256": _sha256(readme),
        },
        "intake": {
            "laboratory_count": len(labs),
            "test_count": len(all_tests),
            "sample_intervals_s": sorted({
                test["median_sample_interval_s"] for test in all_tests
            }),
            "total_time_series_rows": sum(test["row_count"] for test in all_tests),
            "labs": labs,
        },
        "timing_crosswalk": {
            "readme_release_timing_basis": "wall-clock interval for Lab-2 and duration-only for Lab-1",
            "csv_timing_basis": "relative seconds starting at zero",
            "logger_start_wall_clock_present": False,
            "valve_command_or_release_state_channel_present": False,
            "unambiguous_release_to_csv_time_crosswalk_present": False,
        },
        "eligibility_decision": {
            "schema_and_spatial_intake_pass": (
                len(labs) == 2
                and len(all_tests) == 5
                and all(test["median_sample_interval_s"] == 1.0 for test in all_tests)
            ),
            "frozen_detection_timing_validation_eligible": False,
            "frozen_joint_primary_screen_run": False,
            "claim_supported": False,
            "runtime_parameter_application": False,
            "reason": (
                "The public release schedule is not cross-walked to the relative CSV time axis. "
                "Inferring release start from the concentration outcomes would violate the frozen timing protocol."
            ),
            "development_only_spatial_diagnostic_possible": True,
        },
        "privacy_and_redistribution": {
            "raw_rows_committed": False,
            "source_archive_committed": False,
            "aggregate_schema_metrics_only": True,
            "license_notice_required_for_redistribution": True,
        },
        "claim_boundary": (
            "This audit establishes public file integrity, sampling cadence and spatial metadata availability only. "
            "Helium is a surrogate gas, the release-to-logger time crosswalk is absent, and no hydrogen magnitude, "
            "detector latency, placement, ventilation, outdoor dispersion, ESD, safety-distance or full-loop HRS "
            "validation claim is supported."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=ROOT / "data/public_validation/raw/h2safe_2026",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "research/h2safe_public_dataset_intake_2026_10_08.json",
    )
    args = parser.parse_args()
    result = audit(args.raw_dir.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps({
        "output": str(args.output),
        "status": "PASS" if result["eligibility_decision"]["schema_and_spatial_intake_pass"] else "FAIL",
        "timing_validation_eligible": result["eligibility_decision"]["frozen_detection_timing_validation_eligible"],
    }))


if __name__ == "__main__":
    main()
