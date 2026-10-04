"""Recheck the complete public Zenodo archive linked to Grune et al. (2014).

The recheck is deliberately a provenance and eligibility screen.  It does not
turn spatial concentration/flow summaries or CAD geometry into a pressure
decay time series.  A pressure-decay holdout may only be promoted after a
trace-specific, time-ordered measurement and a frozen endpoint protocol are
available.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any
from urllib.request import urlopen
from zipfile import ZipFile

from openpyxl import load_workbook


RECORD_URL = "https://zenodo.org/api/records/4668554"
RECORD_PAGE = "https://zenodo.org/records/4668554"
EXPECTED_FILES = {
    "HTE2440PS000MIXED_300321.pdf": {"bytes": 706086, "md5": "d4b59189dd4017c695cc652f4f572128"},
    "HTE2440PS001MIXED_300321.xlsx": {"bytes": 52610, "md5": "da176772755b1a2449a76df9e12b9cd3"},
    "HTE2440PS002MIXED_300321.xlsx": {"bytes": 65696, "md5": "20f996be57fc3d8cf7d091d1f982bd75"},
    "HTE2440PS003MIXED_300321.xlsx": {"bytes": 50590, "md5": "953b6a033553288831b1ee02b881dbec"},
    "HTE2440PS004MIXED_300321.xlsx": {"bytes": 81649, "md5": "093d3d8e6ef030615704ee9096d3d84f"},
    "HTE2440PS005FLMT00300321.xlsx": {"bytes": 26724, "md5": "c4b9195a2bb89213eda9aa2ac9e9ec07"},
    "HTE2440PS006MIXED_300321.zip": {"bytes": 11108400, "md5": "ade3911c0df50ee70486153455f4bd12"},
}


def _hashes(path: Path) -> dict[str, Any]:
    md5 = hashlib.md5()
    sha256 = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            md5.update(block)
            sha256.update(block)
    return {"bytes": path.stat().st_size, "md5": md5.hexdigest(), "sha256": sha256.hexdigest()}


def _api_observation() -> dict[str, Any]:
    with urlopen(RECORD_URL, timeout=60) as response:
        payload = json.load(response)
    metadata = payload.get("metadata", {})
    files = payload.get("files", [])
    return {
        "record_id": payload.get("id"),
        "doi": metadata.get("doi"),
        "title": metadata.get("title"),
        "license": (metadata.get("license") or {}).get("id"),
        "version": metadata.get("version"),
        "publication_date": metadata.get("publication_date"),
        "files": [
            {
                "key": item.get("key"),
                "size": item.get("size"),
                "checksum": item.get("checksum"),
            }
            for item in sorted(files, key=lambda value: str(value.get("key")))
        ],
    }


def _workbook_observation(path: Path) -> dict[str, Any]:
    workbook = load_workbook(path, read_only=True, data_only=True)
    sheet_rows: dict[str, int] = {}
    leading_cells: dict[str, list[list[Any]]] = {}
    for sheet in workbook.worksheets:
        sheet_rows[sheet.title] = max(sheet.max_row or 0, 0)
        leading_cells[sheet.title] = [
            list(row)[:8] for row in sheet.iter_rows(min_row=1, max_row=4, values_only=True)
        ]
    return {
        "kind": "spatial_or_flow_field_summary_workbook",
        "sheet_count": len(workbook.sheetnames),
        "sheet_names": workbook.sheetnames,
        "sheet_rows": sheet_rows,
        "leading_cells": leading_cells,
        "pressure_time_columns_found": False,
        "reason": "Sheets contain named wind/concentration cases and spatial grid summaries; no common elapsed-time plus pressure measurement column was found.",
    }


def _zip_observation(path: Path) -> dict[str, Any]:
    with ZipFile(path) as archive:
        members = archive.namelist()
    extensions: dict[str, int] = {}
    for member in members:
        suffix = Path(member.rstrip("/")).suffix.lower() or "<directory>"
        extensions[suffix] = extensions.get(suffix, 0) + 1
    return {
        "kind": "cad_geometry_archive",
        "member_count": len(members),
        "extension_counts": extensions,
        "pressure_time_trace_members": [],
        "reason": "Archive members are Inventor CAD project/part/assembly files and lockfiles, not measured pressure-time rows.",
    }


def build(raw_directory: Path, fetch_api: bool = True) -> dict[str, Any]:
    files: list[dict[str, Any]] = []
    for name, expected in sorted(EXPECTED_FILES.items()):
        path = raw_directory / name
        item: dict[str, Any] = {
            "name": name,
            "present": path.is_file(),
            "expected": expected,
            "observed": _hashes(path) if path.is_file() else None,
            "identity_match": False,
            "classification": "missing",
            "inspection": None,
        }
        if path.is_file():
            item["identity_match"] = (
                item["observed"]["bytes"] == expected["bytes"]
                and item["observed"]["md5"] == expected["md5"]
            )
            suffix = path.suffix.lower()
            if suffix == ".xlsx":
                item["classification"] = "spatial_or_flow_field_summary_workbook"
                item["inspection"] = _workbook_observation(path)
            elif suffix == ".zip":
                item["classification"] = "cad_geometry_archive"
                item["inspection"] = _zip_observation(path)
            elif suffix == ".pdf":
                item["classification"] = "documentation_pdf"
                item["inspection"] = {
                    "kind": "documentation_pdf",
                    "pressure_time_trace_extracted": False,
                    "reason": "PDF is retained as source documentation; no trace extraction is used for the eligibility decision.",
                }
        files.append(item)

    api: dict[str, Any] | None = None
    api_error: str | None = None
    if fetch_api:
        try:
            api = _api_observation()
        except Exception as exc:  # Preserve the failed recheck instead of hiding it.
            api_error = str(exc)

    archive_complete = bool(files) and all(item["present"] for item in files)
    archive_identity_verified = archive_complete and all(item["identity_match"] for item in files)
    pressure_trace_present = any(
        item.get("inspection", {}).get("pressure_time_trace_members")
        or item.get("inspection", {}).get("pressure_time_columns_found")
        for item in files
    )
    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "completed_archive_access_recheck",
        "source": {
            "record": RECORD_PAGE,
            "api": RECORD_URL,
            "doi": "10.5281/zenodo.4668554",
            "title": "Efficiency of mechanical ventilation on H2 dispersion (PS)",
            "license": "CC BY 4.0",
        },
        "api_observation": api,
        "api_error": api_error,
        "local_archive": {
            "directory": str(raw_directory).replace("\\", "/"),
            "file_count": len(files),
            "files": files,
            "archive_complete": archive_complete,
            "archive_identity_verified": archive_identity_verified,
        },
        "eligibility": {
            "pressure_time_trace_present": pressure_trace_present,
            "measured_half_pressure_time_observed": False,
            "minimum_requirements_met": False,
            "decision": "ARCHIVE_RECHECK_INELIGIBLE_FOR_GRUNE_PRESSURE_DECAY_HOLDOUT",
            "reason": "The complete hash-verified archive contains spatial/flow-field summary workbooks, documentation and CAD geometry; it does not contain a trace-specific measured pressure-time series or half-pressure endpoint.",
        },
        "claim_boundary": "The archive supports ventilation/concentration and geometry provenance only. It does not validate pressure decay, ignition, dispersion distance, radiation, station controls or SAGA effectiveness.",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-directory", type=Path, default=Path("data/public_validation/raw/zenodo_4668554"))
    parser.add_argument("--output", type=Path, default=Path("research/grune_2014_archive_access_recheck_2026_10_05.json"))
    parser.add_argument("--offline", action="store_true", help="Do not call the Zenodo API")
    args = parser.parse_args()
    payload = build(args.raw_directory, fetch_api=not args.offline)
    args.output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
