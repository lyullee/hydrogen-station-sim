"""Inventory the public H2SAFE indoor surrogate-release package.

This is intentionally an intake and schema evidence builder, rather than a
calibration script.  The published package records helium-surrogate signals;
it does not declare a concentration unit in the CSV headers nor an auditable
mapping between trace ``time=0`` and release onset.  The script therefore
refuses to derive hydrogen alarm thresholds or alter any runtime parameter.

Raw source files remain outside the Git worktree.  The committed result keeps
only hashes, schema/coordinate checks and the explicit evidence boundary.
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
from io import StringIO
import json
import math
from pathlib import Path
from statistics import median
from typing import Any
from xml.etree import ElementTree as ET
import zipfile


DATASET_DOI = "10.7799/17118570"
CATALOG_URL = "https://data.nlr.gov/submissions/330"
LICENSE_URL = "https://data.nlr.gov/node/330/license"
ARCHIVE_URL = "https://data.nlr.gov/system/files/330/1787856683-Dataset.zip"

# Transcribed only from the accompanying official README.  These are used for
# metadata-presence checks, never as fitted model parameters.
EXPECTED_CASES: dict[str, dict[str, Any]] = {
    "Lab1_Small/test1.csv": {
        "lab": "Lab-1",
        "expected_sensor_count": 24,
        "nozzle_diameter_mm": 2.0,
        "orientation": "vertical",
        "nozzle_pressure_psi": 40.0,
        "release_rate_slm": 100.0,
        "release_duration_s": 1389.0,
    },
    "Lab2_Large/test1.csv": {
        "lab": "Lab-2",
        "expected_sensor_count": 37,
        "nozzle_diameter_mm": 0.5,
        "orientation": "horizontal",
        "nozzle_pressure_psi": 220.0,
        "release_rate_slm_range": [92.0, 100.0],
    },
    "Lab2_Large/test2.csv": {
        "lab": "Lab-2",
        "expected_sensor_count": 37,
        "nozzle_diameter_mm": 0.5,
        "orientation": "vertical",
        "nozzle_pressure_psi": 220.0,
        "release_rate_slm_range": [92.0, 100.0],
    },
    "Lab2_Large/test3.csv": {
        "lab": "Lab-2",
        "expected_sensor_count": 37,
        "nozzle_diameter_mm": 1.0,
        "orientation": "vertical",
        "nozzle_pressure_psi": 45.0,
        "release_rate_slm": 100.0,
    },
    "Lab2_Large/test4.csv": {
        "lab": "Lab-2",
        "expected_sensor_count": 37,
        "nozzle_diameter_mm": 1.0,
        "orientation": "vertical",
        "nozzle_pressure_psi": 430.0,
        "release_rate_slm_range": [680.0, 700.0],
    },
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _member_sha256(handle: zipfile.ZipFile, member: str) -> str:
    digest = hashlib.sha256()
    with handle.open(member) as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _document_text(path: Path) -> str:
    namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    with zipfile.ZipFile(path) as archive:
        xml = archive.read("word/document.xml")
    root = ET.fromstring(xml)
    return "\n".join(
        "".join(node.text or "" for node in paragraph.findall(".//w:t", namespace)).strip()
        for paragraph in root.findall(".//w:p", namespace)
    )


def _read_coordinates(handle: zipfile.ZipFile, member: str) -> dict[str, tuple[float, float, float]]:
    rows = csv.DictReader(StringIO(handle.read(member).decode("utf-8-sig")))
    required = {"id", "X", "Y", "Z"}
    if not required.issubset(rows.fieldnames or ()):
        raise ValueError(f"{member}: expected coordinate columns {sorted(required)}")
    coordinates: dict[str, tuple[float, float, float]] = {}
    for row in rows:
        key = str(row["id"]).strip().lower()
        xyz = tuple(float(row[column]) for column in ("X", "Y", "Z"))
        if not key or not all(math.isfinite(value) for value in xyz) or key in coordinates:
            raise ValueError(f"{member}: invalid or duplicated coordinate row")
        coordinates[key] = xyz
    return coordinates


def _read_case_schema(
    handle: zipfile.ZipFile,
    member: str,
    coordinates: dict[str, tuple[float, float, float]],
) -> dict[str, Any]:
    reader = csv.DictReader(StringIO(handle.read(member).decode("utf-8-sig")))
    columns = list(reader.fieldnames or ())
    if not columns or columns[0].strip().lower() != "time":
        raise ValueError(f"{member}: first column must be time")
    sensors = [column.strip().lower() for column in columns[1:]]
    if not sensors or len(sensors) != len(set(sensors)):
        raise ValueError(f"{member}: sensor header is missing or duplicated")
    timestamps: list[float] = []
    measurement_cells = 0
    numeric_cells = 0
    for row in reader:
        try:
            current_time = float(str(row.get(columns[0]) or "").strip())
        except ValueError as exc:
            raise ValueError(f"{member}: nonnumeric time value") from exc
        if not math.isfinite(current_time):
            raise ValueError(f"{member}: nonfinite time value")
        timestamps.append(current_time)
        for column in columns[1:]:
            measurement_cells += 1
            try:
                value = float(str(row.get(column) or "").strip())
            except ValueError:
                continue
            if math.isfinite(value):
                numeric_cells += 1
    if len(timestamps) < 2:
        raise ValueError(f"{member}: fewer than two time samples")
    intervals = [later - earlier for earlier, later in zip(timestamps, timestamps[1:])]
    positive = [interval for interval in intervals if interval > 0.0]
    if len(positive) != len(intervals):
        raise ValueError(f"{member}: time samples are not strictly increasing")
    return {
        "trace_member": member,
        "trace_member_sha256": _member_sha256(handle, member),
        "row_count": len(timestamps),
        "time_start_s": timestamps[0],
        "time_end_s": timestamps[-1],
        "sample_interval_s": {
            "min": min(positive),
            "median": median(positive),
            "max": max(positive),
        },
        "sensor_columns": len(sensors),
        "coordinate_mapped_sensor_columns": sum(sensor in coordinates for sensor in sensors),
        "unmapped_sensor_columns": sorted(sensor for sensor in sensors if sensor not in coordinates),
        "numeric_signal_cell_fraction": numeric_cells / measurement_cells if measurement_cells else 0.0,
        "concentration_unit_declared_in_csv": False,
        "release_start_aligned_to_trace_zero_declared": False,
    }


def build(archive_path: Path, readme_path: Path) -> dict[str, Any]:
    with zipfile.ZipFile(archive_path) as archive:
        members = {info.filename for info in archive.infolist()}
        cases: list[dict[str, Any]] = []
        for member, metadata in EXPECTED_CASES.items():
            if member not in members:
                raise ValueError(f"missing expected H2SAFE trace: {member}")
            coordinate_member = f"{member.rsplit('/', 1)[0]}/sensors.csv"
            if coordinate_member not in members:
                raise ValueError(f"missing coordinates for {member}")
            coordinates = _read_coordinates(archive, coordinate_member)
            schema = _read_case_schema(archive, member, coordinates)
            if len(coordinates) != metadata["expected_sensor_count"]:
                raise ValueError(f"{member}: unexpected coordinate count")
            cases.append({
                "case_id": member.replace("/", ":").removesuffix(".csv"),
                "published_test_metadata": metadata,
                "coordinate_member": coordinate_member,
                "coordinate_member_sha256": _member_sha256(archive, coordinate_member),
                "coordinate_count": len(coordinates),
                **schema,
            })

    readme_text = _document_text(readme_path)
    required_phrases = ["Smaller Lab", "Larger Lab", "Release Rate", "Leak location"]
    return {
        "schema_version": 1,
        "status": "completed_bounded_full_scale_indoor_surrogate_intake",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": {
            "title": "Dataset for H2SAFE - Controlled Gas Releases and Sensor-Response for Indoor Hydrogen Safety",
            "doi": DATASET_DOI,
            "catalog_url": CATALOG_URL,
            "license_url": LICENSE_URL,
            "license_summary": "Use/copy is granted with notice retention and DOE/NLR/Alliance credit in resulting publications.",
            "archive_url": ARCHIVE_URL,
            "archive_sha256": _sha256(archive_path),
            "archive_bytes": archive_path.stat().st_size,
            "readme_sha256": _sha256(readme_path),
            "raw_rows_committed": False,
            "medium": "helium surrogate gas; full-scale indoor laboratory enclosures",
        },
        "intake": {
            "case_count": len(cases),
            "lab_sensor_coordinate_counts": {"Lab-1": 24, "Lab-2": 37},
            "readme_required_sections_present": {
                phrase: phrase in readme_text for phrase in required_phrases
            },
            "case_schema_all_valid": True,
            "cases": cases,
        },
        "eligibility": {
            "full_scale_indoor_geometry_and_sensor_coordinate_context": True,
            "release_and_hvac_metadata_available": True,
            "timestamped_signal_schema_available": True,
            "numerical_hydrogen_alarm_or_trip_threshold_calibration": False,
            "reason_threshold_calibration_closed": (
                "The source CSV headers do not declare concentration units, and the available "
                "metadata does not explicitly align trace time zero to release onset. Helium "
                "surrogate readings must not be treated as hydrogen volume fraction."
            ),
            "full_loop_station_vehicle_validation": False,
            "site_specific_detector_placement_validation": False,
        },
        "runtime_parameter_updated": False,
        "claim_boundary": (
            "This is reproducible public full-scale indoor helium-surrogate data-intake evidence. "
            "It supports only qualitative indoor detector/geometry/HVAC context and regression "
            "checks of metadata handling. It does not calibrate virtual detector amplitude, H2 "
            "alarm or trip setpoints, release physics, detector placement, ESD effectiveness, "
            "outdoor HRS dispersion, consequence distances, or a station-to-vehicle fueling loop."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--readme", type=Path, required=True)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("research/h2safe_indoor_release_intake_2026_10_07.json"),
    )
    args = parser.parse_args()
    result = build(args.archive, args.readme)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.output} from {result['intake']['case_count']} public H2SAFE cases")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
