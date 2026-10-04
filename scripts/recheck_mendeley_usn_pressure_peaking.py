"""Recheck the public Mendeley mirror of the USN pressure-peaking campaign.

The record is a useful, openly licensed consequence-component archive.  This
script inventories the public manifest and verifies that every eligible case
has the raw pressure trace and the synchronized mass-flow channels described
by the data note.  It intentionally does not download or redistribute the
large files and it does not promote the archive to an HRS full-loop holdout:
the experiment is a 14.9 m3 confined enclosure, not a station-to-vehicle
fueling event.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen


DATASET_ID = "pmk59x4hvc"
VERSION = 1
DATASET_PAGE = f"https://data.mendeley.com/datasets/{DATASET_ID}/{VERSION}"
SNAPSHOT_URL = f"https://data.mendeley.com/public-api/datasets/{DATASET_ID}/snapshot/{VERSION}"
FOLDERS_URL = f"https://data.mendeley.com/public-api/datasets/{DATASET_ID}/folders/{VERSION}"
FILES_URL = f"https://data.mendeley.com/public-api/datasets/{DATASET_ID}/files"
EXPECTED_CASES = tuple(range(2, 12))


def _get_json(url: str) -> Any:
    request = Request(
        url,
        headers={
            "Accept": "application/vnd.mendeley-public-dataset.1+json",
            "User-Agent": "hrs-validation-recheck/1.0",
        },
    )
    with urlopen(request, timeout=60) as response:
        return json.load(response)


def _sha256_json(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _file_record(files: list[dict[str, Any]], filename: str) -> dict[str, Any] | None:
    return next((item for item in files if item.get("filename") == filename), None)


def recheck() -> dict[str, Any]:
    snapshot = _get_json(SNAPSHOT_URL)
    folders = _get_json(FOLDERS_URL)
    root_files = _get_json(
        f"{FILES_URL}?folder_id=root&version={VERSION}&%24start=0&%24limit=1000"
    )
    folder_by_name = {str(item.get("name")): item for item in folders}
    files_by_folder: dict[str, list[dict[str, Any]]] = {}
    for folder in folders:
        folder_id = str(folder.get("id"))
        files_by_folder[folder_id] = _get_json(
            f"{FILES_URL}?folder_id={folder_id}&version={VERSION}&%24start=0&%24limit=1000"
        )

    cases: list[dict[str, Any]] = []
    for case in EXPECTED_CASES:
        # The published Mendeley folder for case 11 preserves the original
        # instrument name without the extra zero used by the Zenodo mirror.
        folder_name = "HTE242USN0011MFR190621" if case == 11 else f"HTE242USN{case:05d}MFR190621"
        folder = folder_by_name.get(folder_name)
        folder_files = files_by_folder.get(str((folder or {}).get("id")), [])
        expected = ["CH1_01h.TXT", "CH2_02h.TXT"]
        if case >= 3:
            expected.append("CH3_03h.TXT")
        channel_records = {
            name: _file_record(folder_files, name) for name in expected
        }
        pressure_folder = folder_by_name.get("Gen3i-DATA")
        pressure_files = files_by_folder.get(str((pressure_folder or {}).get("id")), [])
        pressure_name = f"HTE242USN{case:05d}PRESS190621.txt"
        pressure = _file_record(pressure_files, pressure_name)
        cases.append(
            {
                "case": case,
                "mfr_folder": folder_name,
                "mfr_folder_present": folder is not None,
                "channels": {
                    name: {
                        "id": item.get("id"),
                        "size": item.get("size"),
                        "sha256": (item.get("content_details") or {}).get("sha256_hash"),
                        "content_type": (item.get("content_details") or {}).get("content_type"),
                    }
                    if item
                    else None
                    for name, item in channel_records.items()
                },
                "pressure_trace": {
                    "filename": pressure_name,
                    "id": pressure.get("id"),
                    "size": pressure.get("size"),
                    "sha256": (pressure.get("content_details") or {}).get("sha256_hash"),
                    "content_type": (pressure.get("content_details") or {}).get("content_type"),
                }
                if pressure
                else None,
            }
        )

    eligible_cases = [
        item
        for item in cases
        if item["mfr_folder_present"]
        and item["pressure_trace"] is not None
        and all(item["channels"].get(name) is not None for name in ("CH1_01h.TXT", "CH2_02h.TXT"))
    ]
    description = _file_record(root_files, "File's description.docx")
    license_name = ((snapshot.get("licence") or {}).get("short_name"))
    all_case_identity = all(
        item["mfr_folder_present"]
        and item["pressure_trace"] is not None
        and item["channels"].get("CH1_01h.TXT") is not None
        and item["channels"].get("CH2_02h.TXT") is not None
        for item in cases
    )
    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "completed_public_manifest_recheck",
        "source": {
            "dataset_id": DATASET_ID,
            "version": VERSION,
            "doi": snapshot.get("doi"),
            "title": snapshot.get("name"),
            "landing_page": DATASET_PAGE,
            "snapshot_api": SNAPSHOT_URL,
            "license": license_name,
            "publisher_institution": [item.get("name") for item in (snapshot.get("institutions") or [])],
            "raw_files_not_committed": True,
        },
        "public_manifest": {
            "folder_count": len(folders),
            "root_description_present": description is not None,
            "root_description_sha256": ((description or {}).get("content_details") or {}).get("sha256_hash"),
            "case_count_expected": len(EXPECTED_CASES),
            "case_count_with_pressure_and_mass_flow": len(eligible_cases),
            "all_case_identities_present": all_case_identity,
            "case_records": cases,
            "manifest_sha256": _sha256_json(cases),
        },
        "eligibility": {
            "raw_pressure_time_series_present": len(eligible_cases) == len(EXPECTED_CASES),
            "raw_mass_flow_channel_present": len(eligible_cases) == len(EXPECTED_CASES),
            "vent_geometry_and_initial_conditions_in_dataset_manifest": False,
            "requires_associated_publication_for_setup_mapping": True,
            "component_consequence_holdout_eligible": license_name == "CC BY 4.0" and all_case_identity,
            "full_loop_external_holdout_eligible": False,
            "decision": "CONSEQUENCE_COMPONENT_ARCHIVE_ONLY",
        },
        "claim_boundary": (
            "This CC BY 4.0 archive provides raw pressure and Coriolis mass-flow channels "
            "for ten confined-enclosure experiments and is suitable for reproducible "
            "pressure-peaking consequence checks. It is not a gaseous H70 station-to-vehicle "
            "fueling loop, does not include station control or dispenser logs, and cannot "
            "establish full-loop digital-twin or SAGA effectiveness."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("research/mendeley_usn_pressure_peaking_manifest_2026_10_05.json"),
    )
    args = parser.parse_args()
    result = recheck()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "eligible_cases": result["public_manifest"]["case_count_with_pressure_and_mass_flow"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
