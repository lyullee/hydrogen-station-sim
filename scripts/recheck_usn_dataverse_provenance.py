"""Recheck canonical DataverseNO provenance for the public USN/FFI H2 archive.

Only public file metadata and local archive digests are retained.  CSV rows,
headers, source paths and timestamps are never written to the repository.  A
successful checksum match confirms provenance, not model validation or an
independent holdout.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen


DATASET_DOI = "10.23642/USN.26117989"
API_URL = "https://dataverse.no/api/datasets/:persistentId/?" + urlencode(
    {"persistentId": f"doi:{DATASET_DOI}"}
)


def _md5(path: Path) -> str:
    digest = hashlib.md5()  # noqa: S324 - matches the public Dataverse checksum.
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _fetch_metadata() -> dict[str, Any]:
    request = Request(API_URL, headers={"Accept": "application/json"})
    with urlopen(request, timeout=60) as response:  # noqa: S310 - fixed HTTPS URL.
        return json.loads(response.read().decode("utf-8"))


def _public_archive_metadata(payload: dict[str, Any]) -> dict[str, Any]:
    latest = ((payload.get("data") or {}).get("latestVersion") or {})
    files = latest.get("files") or []
    archives = []
    for item in files:
        data_file = item.get("dataFile") or {}
        name = str(data_file.get("filename") or "")
        if name.startswith("23_FFI_P101_T") and name.endswith(".zip"):
            checksum = data_file.get("checksum") or {}
            archives.append(
                {
                    "filename": name,
                    "bytes": int(data_file.get("filesize") or 0),
                    "md5": str(checksum.get("value") or data_file.get("md5") or "").lower(),
                    "file_id": int(data_file.get("id") or 0),
                }
            )
    archives.sort(key=lambda item: item["filename"])
    license_info = latest.get("license") or {}
    return {
        "dataset_id": payload.get("data", {}).get("id"),
        "identifier": payload.get("data", {}).get("identifier"),
        "doi": DATASET_DOI,
        "version": f"{latest.get('versionNumber')}.{latest.get('versionMinorNumber')}",
        "publication_date": latest.get("publicationDate"),
        "license": license_info.get("name"),
        "license_uri": license_info.get("uri"),
        "archive_count": len(archives),
        "archives": archives,
    }


def compare_local_archives(metadata: dict[str, Any], raw_dir: Path | None) -> dict[str, Any]:
    expected = {item["filename"]: item for item in metadata["archives"]}
    if raw_dir is None:
        return {
            "checked": False,
            "local_archive_count": None,
            "matched_count": None,
            "missing_public_files": None,
            "extra_local_files": None,
            "all_public_md5_match": None,
        }
    local = {path.name: path for path in raw_dir.glob("23_FFI_P101_T*.zip")}
    matched = sum(
        name in expected and _md5(path) == expected[name]["md5"]
        for name, path in local.items()
    )
    missing = sorted(set(expected) - set(local))
    extra = sorted(set(local) - set(expected))
    all_match = len(local) == len(expected) and not missing and not extra and matched == len(expected)
    return {
        "checked": True,
        "local_archive_count": len(local),
        "matched_count": matched,
        "missing_public_files": missing,
        "extra_local_files": extra,
        "all_public_md5_match": all_match,
    }


def build_report(payload: dict[str, Any], raw_dir: Path | None) -> dict[str, Any]:
    metadata = _public_archive_metadata(payload)
    local_check = compare_local_archives(metadata, raw_dir)
    # File names/IDs are public provenance metadata; no measurement rows or
    # original CSV headers are copied into this report.
    return {
        "schema_version": 1,
        "artifact_type": "usn_dataverse_public_provenance_recheck",
        "recorded_at": "2026-10-14",
        "source": {
            "doi": metadata["doi"],
            "api_url": API_URL,
            "dataverse_identifier": metadata["identifier"],
            "dataset_version": metadata["version"],
            "publication_date": metadata["publication_date"],
            "license": metadata["license"],
            "license_uri": metadata["license_uri"],
            "public_archive_count": metadata["archive_count"],
            "public_archive_bytes": sum(item["bytes"] for item in metadata["archives"]),
            "public_archive_md5_count": sum(bool(item["md5"]) for item in metadata["archives"]),
        },
        "local_comparison": local_check,
        "decision": {
            "provenance_integrity": bool(
                metadata["archive_count"] == 22
                and metadata["license"] == "CC BY 4.0"
                and local_check.get("all_public_md5_match") is True
            ) if local_check["checked"] else False,
            "independent_holdout": False,
            "runtime_parameter_application": False,
            "reason": (
                "The archive is a public actual-hydrogen component dataset and its local files "
                "match the canonical Dataverse metadata, but outcomes were already accessed "
                "during candidate development; it remains provenance/development evidence."
            ),
        },
        "claim_boundary": (
            "This record verifies public source identity, CC BY 4.0 terms and file digests only. "
            "It does not validate concentration magnitude, detector placement, alarm timing, "
            "outdoor HRS dispersion, ESD, consequence distance or station-to-vehicle behavior."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, default=None)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    raw_dir = args.raw_dir.resolve() if args.raw_dir else None
    if raw_dir is not None and not raw_dir.is_dir():
        parser.error(f"raw directory does not exist: {raw_dir}")
    report = build_report(_fetch_metadata(), raw_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "decision": report["decision"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
