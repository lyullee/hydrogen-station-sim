"""Inventory the public USN/FFI actual-hydrogen channel dataset.

The Figshare record contains 22 ZIP archives with time-resolved hydrogen
concentration, mass-flow and pressure channels.  This command records only
publication metadata and bounded schema checks from explicitly supplied local
sample archives.  It never commits the public raw rows and never promotes the
channel experiment to an HRS or runtime validation gate.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import io
import json
import re
import urllib.request
import zipfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
API_URL = "https://api.figshare.com/v2/articles/26117989"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _api_record() -> dict[str, Any]:
    request = urllib.request.Request(API_URL, headers={"User-Agent": "h2station-evidence-audit"})
    with urllib.request.urlopen(request, timeout=30) as response:
        value = json.load(response)
    if not isinstance(value, dict):
        raise ValueError("Figshare API did not return an object")
    return value


def _experiment_mapping(description: str) -> list[dict[str, str]]:
    text = html.unescape(re.sub(r"<[^>]+>", "\n", description or ""))
    return [
        {"archive_stem": archive, "article_test": article.strip()}
        for archive, article in re.findall(
            r"(23_FFI_P101_T\d+)\s*-\s*(test-[0-9A-Za-z-]+)", text
        )
    ]


def _sample_schema(path: Path) -> dict[str, Any]:
    with zipfile.ZipFile(path) as archive:
        members = [name for name in archive.namelist() if name.lower().endswith(".csv")]
        if len(members) != 1:
            raise ValueError(f"expected exactly one CSV in {path.name}")
        member = members[0]
        payload = archive.read(member)
    stream = io.StringIO(payload.decode("utf-8-sig", errors="replace"), newline="")
    rows = csv.reader(stream)
    headers = next(rows)
    row_count = sum(1 for _ in rows)
    sensor_headers = [
        header
        for header in headers
        if "h2 concentration" in header.lower() and "[%]" in header
    ]
    required_headers = {
        "flow time [s]",
        "filling pressure [bar]",
        "h2 sensor time",
    }
    has_mass_flow = any(
        re.fullmatch(r"mass flow meter \d+ \[g/s\]", header.lower())
        for header in headers
    )
    return {
        "archive": path.name,
        "csv_member": member.split("/")[-1],
        "archive_sha256": _sha256(path),
        "row_count": row_count,
        "column_count": len(headers),
        "hydrogen_sensor_column_count": len(sensor_headers),
        "required_time_pressure_flow_headers": required_headers.issubset(set(headers)) and has_mass_flow,
        "concentration_unit_declared": any(
            "h2 concentration" in header.lower() and "[%]" in header for header in headers
        ),
        "raw_rows_committed": False,
    }


def audit(record: dict[str, Any], sample_archives: list[Path]) -> dict[str, Any]:
    files = [item for item in record.get("files") or [] if str(item.get("name", "")).lower().endswith(".zip")]
    mappings = _experiment_mapping(str(record.get("description") or ""))
    sample_schemas = [_sample_schema(path) for path in sample_archives]
    source = {
        "article_id": int(record.get("id")),
        "doi": str(record.get("doi") or "10.23642/USN.26117989.v2"),
        "title": str(record.get("title") or ""),
        "api_url": API_URL,
        "landing_url": "https://figshare.com/articles/dataset/Experimental_Data_of_Hydrogen_Dispersion_in_an_Open-ended_Rectangular_Channel/26117989",
        "license": ((record.get("license") or {}).get("name")),
        "license_url": ((record.get("license") or {}).get("url")),
        "published_date": record.get("published_date"),
        "article_doi": "10.1016/j.jlp.2025.105669",
    }
    schema_pass = bool(
        sample_schemas
        and all(item["column_count"] == 37 for item in sample_schemas)
        and all(item["hydrogen_sensor_column_count"] == 29 for item in sample_schemas)
        and all(item["required_time_pressure_flow_headers"] for item in sample_schemas)
        and all(item["concentration_unit_declared"] for item in sample_schemas)
    )
    return {
        "schema_version": 1,
        "artifact_type": "public_actual_h2_channel_dataset_inventory",
        "recorded_at": "2026-10-12",
        "source": source,
        "dataset_scope": {
            "experiment_count": len(files),
            "file_count": len(files),
            "mapping_count": len(mappings),
            "actual_hydrogen": True,
            "sensor_count": 29,
            "channel_families": ["mass flow", "filling pressure", "hydrogen concentration"],
            "geometry_context": "5.8 m x 0.9 m x 0.8 m open-ended rectangular channel; empty and beam-obstruction conditions",
            "published_test_period": "2023-04",
        },
        "publication_file_inventory": [
            {
                "name": str(item.get("name")),
                "size_bytes": int(item.get("size") or 0),
                "md5": str(item.get("computed_md5") or item.get("supplied_md5") or ""),
                "download_url": str(item.get("download_url") or ""),
            }
            for item in files
        ],
        "experiment_mapping": mappings,
        "sample_schema_checks": sample_schemas,
        "eligibility": {
            "schema_screen_pass": schema_pass,
            "independent_actual_hydrogen_component_candidate": schema_pass,
            "spatial_sensor_coordinate_table_present_in_sample": False,
            "station_to_vehicle_full_loop": False,
            "runtime_parameter_application": False,
            "validation_gate_promoted": False,
        },
        "next_action": "Freeze a geometry-aware, concentration-unit-preserving pre-access protocol using the published Table 1 sensor coordinates and reserve disjoint experiment IDs before reading outcome rows.",
        "claim_boundary": "This is a public actual-hydrogen component-data inventory and schema screen. It does not validate the station twin, HRS consequence distances, ESD, vehicle filling, SAGA effectiveness, or any runtime parameter.",
    }


def _markdown(result: dict[str, Any]) -> str:
    scope = result["dataset_scope"]
    eligibility = result["eligibility"]
    lines = [
        "# Public actual-hydrogen channel dataset inventory",
        "",
        f"- DOI: `https://doi.org/{result['source']['doi']}`",
        f"- Article DOI: `https://doi.org/{result['source']['article_doi']}`",
        f"- Experiments/files: `{scope['experiment_count']}`",
        f"- Hydrogen sensors per experiment: `{scope['sensor_count']}`",
        f"- Schema screen: **{'PASS' if eligibility['schema_screen_pass'] else 'FAIL'}**",
        "- Runtime application: **false**",
        "",
        "The public record contains actual-hydrogen concentration, mass-flow and filling-pressure time series under empty-channel and beam-obstruction conditions. Raw rows are not committed by this project.",
        "",
        "## Boundary",
        "",
        "The archive is a component-scale open-channel experiment, not an HRS station-to-vehicle trace. A new spatial protocol must freeze the sensor-coordinate mapping and disjoint experiment IDs before numerical outcome scoring.",
        "",
        f"> {result['claim_boundary']}",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample-archive", action="append", type=Path, default=[])
    parser.add_argument("--output", type=Path, default=ROOT / "research/public_actual_h2_channel_dataset_inventory_2026_10_12.json")
    parser.add_argument("--markdown", type=Path, default=ROOT / "research/PUBLIC_ACTUAL_H2_CHANNEL_DATASET_INVENTORY_2026_10_12.md")
    args = parser.parse_args()
    result = audit(_api_record(), [path.resolve() for path in args.sample_archive])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.markdown.write_text(_markdown(result), encoding="utf-8")
    print(json.dumps({"output": str(args.output), "experiment_count": result["dataset_scope"]["experiment_count"], "schema_screen_pass": result["eligibility"]["schema_screen_pass"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
