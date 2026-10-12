"""Audit the H2SAFE HVAC metadata needed by a spatial detector candidate.

The public H2SAFE package publishes sensor traces, a sensor coordinate table,
and a DOCX describing releases and HVAC equipment.  This audit deliberately
records only aggregate metadata and hashes; it never copies the raw traces or
promotes a development candidate into the runtime model.  Its purpose is to
make the next pre-access spatial validation reproducible and fail closed when
one of the required common-frame inputs is missing.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import zipfile
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _paragraphs(path: Path) -> list[str]:
    """Read DOCX paragraph text without requiring python-docx."""

    with zipfile.ZipFile(path) as archive:
        xml = archive.read("word/document.xml")
    root = ET.fromstring(xml)
    return [
        "".join(node.text or "" for node in paragraph.findall(".//w:t", NS)).strip()
        for paragraph in root.findall(".//w:p", NS)
        if "".join(node.text or "" for node in paragraph.findall(".//w:t", NS)).strip()
    ]


def _find_index(paragraphs: list[str], value: str) -> int:
    try:
        return paragraphs.index(value)
    except ValueError as exc:
        raise ValueError(f"H2SAFE metadata is missing expected paragraph: {value!r}") from exc


def _lab1_release(paragraphs: list[str]) -> dict[str, Any]:
    start = _find_index(paragraphs, "Smaller Lab – Lab 1")
    row = paragraphs[start + 9 : start + 16]
    if row[:1] != ["Test 1"] or len(row) != 7:
        raise ValueError("Unexpected Lab 1 release metadata layout")
    return {
        "test_id": row[0],
        "sensor_count": int(row[1]),
        "nozzle_size": row[2],
        "orientation": row[3].lower(),
        "pressure": row[4],
        "release_rate": row[5],
        "release_duration": row[6],
        "release_location": paragraphs[start + 16],
    }


def _lab1_vents(paragraphs: list[str]) -> list[dict[str, Any]]:
    start = _find_index(paragraphs, "Vent")
    end = _find_index(paragraphs, "NS (Normal to surface)")
    # Skip the four column headers (In/Out, Angle, Area and velocity).
    values = paragraphs[start + 5 : end]
    if len(values) % 5:
        raise ValueError("Unexpected Lab 1 HVAC metadata layout")
    records = []
    for offset in range(0, len(values), 5):
        name, io, angle, area, speed = values[offset : offset + 5]
        records.append({
            "name": name,
            "flow_role": io,
            "angle_text": angle,
            "area_m2": float(area),
            "speed_m_s": float(speed),
        })
    return records


def _lab2_vents(paragraphs: list[str]) -> list[dict[str, Any]]:
    start = _find_index(paragraphs, "Duct No.")
    end = _find_index(paragraphs, "Equipment")
    values = paragraphs[start + 4 : end]
    records: list[dict[str, Any]] = []
    index = 0
    while index < len(values):
        duct_number = values[index]
        if not duct_number.isdigit():
            index += 1
            continue
        location = values[index + 1] if index + 1 < len(values) and not values[index + 1].isdigit() else None
        area = values[index + 2] if location is not None else values[index + 1]
        speed = values[index + 3] if location is not None else values[index + 2]
        records.append({
            "duct_number": int(duct_number),
            "location": location,
            "area_in2": float(area),
            "speed_m_s": float(speed),
        })
        index += 4 if location is not None else 3
    return records


def _lab2_fans(paragraphs: list[str]) -> list[dict[str, Any]]:
    start = _find_index(paragraphs, "Equipment")
    end = _find_index(paragraphs, "Each recirculation duct inlet(s) is 80 in2 area")
    values = paragraphs[start + 3 : end]
    records = []
    for index in range(0, len(values), 3):
        if index + 2 >= len(values):
            break
        records.append({
            "name": values[index],
            "speed_m_s": float(values[index + 1]),
            "pressure_drop_pa": float(values[index + 2]),
        })
    return records


def _lab2_releases(paragraphs: list[str]) -> list[dict[str, Any]]:
    lab2_start = _find_index(paragraphs, "Larger Lab – Lab 2")
    start = paragraphs.index("Test", lab2_start)
    note = "*SLM denotes standard liters per minute. Individual test files may contain measurements from only a subset of the listed sensor locations."
    end = paragraphs.index(note, start)
    values = paragraphs[start + 1 : end]
    records = []
    index = 0
    while index < len(values):
        if not re.fullmatch(r"Test \d+", values[index]):
            index += 1
            continue
        if index + 6 >= len(values):
            raise ValueError("Unexpected Lab 2 release metadata layout")
        records.append({
            "test_id": values[index],
            "date": values[index + 1],
            "nozzle_size": values[index + 2],
            "orientation": values[index + 3].lower(),
            "pressure": values[index + 4],
            "release_rate": values[index + 5],
            "release_time": values[index + 6],
        })
        index += 7
    return records


def _coordinate_summary(paragraphs: list[str]) -> dict[str, Any]:
    start = _find_index(paragraphs, "Leak location coordinates (X, Y, Z) (in meters)")
    coordinate_re = re.compile(r"^\((-?[0-9.]+),\s*(-?[0-9.]+),\s*(-?[0-9.]+)\)$")
    coordinates: dict[str, list[float]] = {}
    for value in paragraphs[start + 1 : start + 6]:
        match = coordinate_re.match(value)
        if match:
            # The preceding paragraph is Lab-1/Lab-2.
            label = paragraphs[paragraphs.index(value) - 1].replace("-", "_").lower()
            coordinates[label] = [float(part) for part in match.groups()]
    return {
        "coordinates_m": coordinates,
        "declared_common_sensor_reference_frame": paragraphs[start + 5].startswith(
            "All four Lab-2 tests use the same coordinates"
        ),
    }


def audit(metadata_path: Path) -> dict[str, Any]:
    paragraphs = _paragraphs(metadata_path)
    lab1_vents = _lab1_vents(paragraphs)
    lab2_vents = _lab2_vents(paragraphs)
    lab2_fans = _lab2_fans(paragraphs)
    releases = {
        "lab_1": [_lab1_release(paragraphs)],
        "lab_2": _lab2_releases(paragraphs),
    }
    direction_input = {
        "release_direction_vector": {
            "available": False,
            "declared_orientation_only": True,
            "reason": "The metadata declares horizontal/vertical orientation but no azimuth or common-frame 3-D jet vector.",
        },
        "ventilation_velocity_vectors": {
            "available": False,
            "lab_1_speed_and_area_records": len(lab1_vents),
            "lab_2_duct_speed_and_area_records": len(lab2_vents),
            "lab_2_recirculation_fan_records": len(lab2_fans),
            "direction_text_records": sum(record["angle_text"] != "NS" for record in lab1_vents),
            "reason": "Speeds and areas are published, but the vents/ducts lack origins and common-frame 3-D vectors.",
        },
        "obstruction_geometry": {
            "mesh_files_present": True,
            "coordinate_registration_validated": False,
            "reason": "STEP/STL meshes are present, but no independently checked registration from mesh coordinates to sensor coordinates is declared.",
        },
        "release_to_trace_time_crosswalk": {
            "available": False,
            "reason": "Release wall-clock/duration metadata is not aligned to the CSV-relative logger time axis.",
        },
    }
    missing = [
        name
        for name, field in direction_input.items()
        if field.get("available") is False or field.get("coordinate_registration_validated") is False
    ]
    return {
        "schema_version": 1,
        "artifact_type": "h2safe_hvac_spatial_input_readiness_audit",
        "recorded_at": "2026-10-12",
        "source": {
            "title": "Dataset for H2SAFE - Controlled Gas Releases and Sensor-Response for Indoor Hydrogen Safety",
            "doi": "10.7799/17118570",
            "test_gas": "helium surrogate",
            "metadata_file": metadata_path.name,
            "metadata_sha256": _sha256(metadata_path),
            "metadata_bytes": metadata_path.stat().st_size,
        },
        "parsed_metadata": {
            "release_tests": releases,
            "lab_1_vent_count": len(lab1_vents),
            "lab_2_duct_count": len(lab2_vents),
            "lab_2_recirculation_fan_count": len(lab2_fans),
            "lab_1_vent_speed_area_records": lab1_vents,
            "lab_2_duct_speed_area_records": lab2_vents,
            "lab_2_recirculation_fans": lab2_fans,
            "coordinates": _coordinate_summary(paragraphs),
        },
        "required_common_frame_inputs": direction_input,
        "decision": {
            "status": "NOT_READY_FOR_PREACCESS_SPATIAL_VALIDATION" if missing else "READY_FOR_PREACCESS_SPATIAL_VALIDATION",
            "missing_inputs": missing,
            "runtime_application": False,
            "development_candidate_use": "permitted only for schema/unit tests; no outcome-based score claims",
            "next_action": "Obtain a rights-cleared cohort with release vectors, HVAC vectors, registered obstruction geometry, signal units and a release-to-trace time crosswalk, then freeze candidate before outcome access.",
        },
        "claim_boundary": "This audit parses public HVAC metadata and makes missing common-frame inputs explicit. It is not a hydrogen concentration model, CFD result, detector placement validation, alarm/ESD validation, consequence-distance estimate or HRS full-loop validation.",
    }


def _markdown(result: dict[str, Any]) -> str:
    decision = result["decision"]
    inputs = result["required_common_frame_inputs"]
    lines = [
        "# H2SAFE HVAC spatial-input readiness",
        "",
        f"- Status: **{decision['status']}**",
        f"- Source DOI: `https://doi.org/{result['source']['doi']}`",
        f"- Metadata SHA-256: `{result['source']['metadata_sha256']}`",
        "- Runtime application: **false**",
        "",
        "## Parsed public metadata",
        "",
        f"- Release tests: Lab 1 `{len(result['parsed_metadata']['release_tests']['lab_1'])}`, Lab 2 `{len(result['parsed_metadata']['release_tests']['lab_2'])}`",
        f"- Lab 1 ventilation records: `{result['parsed_metadata']['lab_1_vent_count']}`",
        f"- Lab 2 duct records: `{result['parsed_metadata']['lab_2_duct_count']}`",
        f"- Lab 2 recirculation fans: `{result['parsed_metadata']['lab_2_recirculation_fan_count']}`",
        "",
        "## Required inputs",
        "",
    ]
    for name, field in inputs.items():
        available = field.get("available", field.get("coordinate_registration_validated"))
        lines.append(f"- `{name}`: **{'available' if available else 'missing'}** — {field['reason']}")
    lines.extend([
        "",
        "## Gate interpretation",
        "",
        "The metadata is sufficient to write a transparent candidate and unit-test parser behavior. It is not sufficient for a pre-access spatial validation because the release/HVAC vectors, registered obstruction geometry and release-time crosswalk are not jointly declared in one frame.",
        "",
        f"Next action: {decision['next_action']}",
        "",
        f"> {result['claim_boundary']}",
        "",
    ])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--metadata",
        type=Path,
        default=ROOT / "data/public_validation/raw/h2safe_2026/HVAC_information.docx",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "research/h2safe_hvac_input_readiness_2026_10_12.json",
    )
    parser.add_argument(
        "--markdown",
        type=Path,
        default=ROOT / "research/H2SAFE_HVAC_INPUT_READINESS_2026_10_12.md",
    )
    args = parser.parse_args()
    result = audit(args.metadata.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.markdown.write_text(_markdown(result), encoding="utf-8")
    print(json.dumps({"output": str(args.output), "status": result["decision"]["status"], "missing_inputs": result["decision"]["missing_inputs"]}))


if __name__ == "__main__":
    main()
