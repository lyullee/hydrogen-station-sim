"""Audit public H2SAFE mesh/sensor containment without promoting a model.

The OEDI H2SAFE package publishes ASCII STL/STEP laboratory geometry and sensor
coordinates.  This audit checks a narrow, pre-access invariant: every published
sensor coordinate and the documented release coordinate fall inside the matching
mesh bounding box.  Bounding-box containment is useful evidence that a common
frame may be recoverable, but it is not an independent registration, CFD result,
or spatial-response validation.  Raw files remain local inputs and are never
copied into the committed artifact.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

# Allow direct ``python scripts/...`` execution as well as module imports.
if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.audit_h2safe_hvac_input_readiness import _coordinate_summary, _paragraphs


ROOT = Path(__file__).resolve().parents[1]
_VERTEX = re.compile(
    rb"vertex\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)"
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _sensor_points(path: Path) -> list[tuple[str, tuple[float, float, float]]]:
    with path.open(newline="", encoding="utf-8-sig") as stream:
        rows = csv.DictReader(stream)
        required = {"id", "X", "Y", "Z"}
        if not required.issubset(rows.fieldnames or set()):
            raise ValueError(f"sensor coordinate columns missing in {path}")
        return [
            (
                str(row["id"]),
                (float(row["X"]), float(row["Y"]), float(row["Z"])),
            )
            for row in rows
        ]


def _stl_bounds(path: Path) -> dict[str, list[float]]:
    values = [tuple(float(part) for part in match) for match in _VERTEX.findall(path.read_bytes())]
    if not values:
        raise ValueError(f"no ASCII STL vertices found in {path}")
    return {
        "min_m": [min(point[index] for point in values) for index in range(3)],
        "max_m": [max(point[index] for point in values) for index in range(3)],
        "vertex_count": len(values),
    }


def _inside(bounds: dict[str, list[float]], point: tuple[float, float, float], tolerance: float = 1e-6) -> bool:
    return all(
        bounds["min_m"][index] - tolerance <= point[index] <= bounds["max_m"][index] + tolerance
        for index in range(3)
    )


def _bounds(points: list[tuple[str, tuple[float, float, float]]]) -> dict[str, list[float]]:
    values = [point for _, point in points]
    return {
        "min_m": [min(point[index] for point in values) for index in range(3)],
        "max_m": [max(point[index] for point in values) for index in range(3)],
    }


def audit(dataset_root: Path, metadata_path: Path, archive_path: Path | None = None) -> dict[str, Any]:
    source = {
        "title": "Dataset for H2SAFE - Controlled Gas Releases and Sensor-Response for Indoor Hydrogen Safety",
        "doi": "10.7799/17118570",
        "catalog_url": "https://data.openei.org/submissions/8799",
        "archive_url": "https://data.nlr.gov/system/files/330/1787856683-Dataset.zip",
        "hvac_metadata_url": "https://data.nlr.gov/system/files/330/1788206575-HVAC_information.docx",
        "dataset_package": "Dataset.zip",
        "dataset_package_sha256": _sha256(archive_path) if archive_path and archive_path.exists() else None,
        "hvac_metadata_sha256": _sha256(metadata_path) if metadata_path.exists() else None,
    }
    paragraphs = _paragraphs(metadata_path)
    coordinate_map = _coordinate_summary(paragraphs)["coordinates_m"]
    labs = {
        "lab_1": ("Lab1_Small", "lab_1"),
        "lab_2": ("Lab2_Large", "lab_2"),
    }
    records: dict[str, Any] = {}
    all_sensor_count = 0
    all_sensor_inside = 0
    release_inside: dict[str, bool] = {}
    for lab_key, (directory, coordinate_key) in labs.items():
        lab_root = dataset_root / directory
        mesh = lab_root / ("Lab1_small.STL" if lab_key == "lab_1" else "Lab2_Large.STL")
        sensors = _sensor_points(lab_root / "sensors.csv")
        mesh_bounds = _stl_bounds(mesh)
        sensor_bounds = _bounds(sensors)
        sensor_inside = [sensor_id for sensor_id, point in sensors if _inside(mesh_bounds, point)]
        release = tuple(coordinate_map[coordinate_key])
        release_ok = _inside(mesh_bounds, release)
        all_sensor_count += len(sensors)
        all_sensor_inside += len(sensor_inside)
        release_inside[lab_key] = release_ok
        records[lab_key] = {
            "mesh_file": f"extracted/{directory}/{mesh.name}",
            "sensor_file": f"extracted/{directory}/sensors.csv",
            "mesh_bounds_m": mesh_bounds,
            "sensor_bounds_m": sensor_bounds,
            "sensor_count": len(sensors),
            "sensor_inside_mesh_count": len(sensor_inside),
            "sensor_containment_fraction": len(sensor_inside) / len(sensors),
            "release_coordinate_m": list(release),
            "release_inside_mesh_bounds": release_ok,
        }
    containment_fraction = all_sensor_inside / all_sensor_count
    status = "CONTAINMENT_CONFIRMED_REGISTRATION_UNPROVEN"
    return {
        "schema_version": 1,
        "artifact_type": "h2safe_geometry_sensor_containment_diagnostic",
        "recorded_at": "2026-10-12",
        "source": source,
        "labs": records,
        "summary": {
            "sensor_count": all_sensor_count,
            "sensor_inside_mesh_count": all_sensor_inside,
            "sensor_containment_fraction": containment_fraction,
            "release_inside_mesh_bounds": release_inside,
            "all_sensor_points_inside_mesh_bounds": all_sensor_inside == all_sensor_count,
            "all_release_points_inside_mesh_bounds": all(release_inside.values()),
            "status": status,
        },
        "decision": {
            "runtime_application": False,
            "preaccess_spatial_validation_ready": False,
            "interpretation": "The public geometry and sensor/release coordinates are mutually contained at bounding-box level. This does not prove mesh-to-sensor registration, vent vectors, release azimuth, obstruction semantics, or time alignment.",
            "next_action": "Use the published meshes as a candidate obstruction frame only after an independently documented registration and a release-to-trace clock crosswalk are frozen.",
        },
        "claim_boundary": "This is a geometry-containment diagnostic only. It is not a CFD result, detector-placement validation, hydrogen-model calibration, consequence-distance estimate, or runtime safety claim.",
    }


def _markdown(result: dict[str, Any]) -> str:
    summary = result["summary"]
    lines = [
        "# H2SAFE geometry and sensor containment diagnostic",
        "",
        f"- Status: **{summary['status']}**",
        f"- Source DOI: `https://doi.org/{result['source']['doi']}`",
        f"- Sensor containment: `{summary['sensor_inside_mesh_count']}/{summary['sensor_count']}` (`{summary['sensor_containment_fraction']:.3f}`)",
        f"- Release points inside mesh bounds: `{summary['release_inside_mesh_bounds']}`",
        "- Runtime application: **false**",
        "",
        "## Interpretation",
        "",
        result["decision"]["interpretation"],
        "",
        "## Lab-level checks",
        "",
    ]
    for lab, record in result["labs"].items():
        lines.append(
            f"- `{lab}`: sensors `{record['sensor_inside_mesh_count']}/{record['sensor_count']}` inside the STL bounding box; release point inside bounds `{record['release_inside_mesh_bounds']}`."
        )
    lines.extend(["", f"Next action: {result['decision']['next_action']}", "", f"> {result['claim_boundary']}", ""])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-root", type=Path, default=ROOT / "data/public_validation/raw/h2safe_2026/extracted")
    parser.add_argument("--metadata", type=Path, default=ROOT / "data/public_validation/raw/h2safe_2026/HVAC_information.docx")
    parser.add_argument("--archive", type=Path, default=ROOT / "data/public_validation/raw/h2safe_2026/Dataset.zip")
    parser.add_argument("--output", type=Path, default=ROOT / "research/h2safe_geometry_sensor_containment_2026_10_12.json")
    parser.add_argument("--markdown", type=Path, default=ROOT / "research/H2SAFE_GEOMETRY_SENSOR_CONTAINMENT_2026_10_12.md")
    args = parser.parse_args()
    result = audit(args.dataset_root.resolve(), args.metadata.resolve(), args.archive.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.markdown.write_text(_markdown(result), encoding="utf-8")
    print(json.dumps({"output": str(args.output), **result["summary"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
