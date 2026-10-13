from __future__ import annotations

from pathlib import Path

from scripts.recheck_usn_dataverse_provenance import (
    _public_archive_metadata,
    compare_local_archives,
)


def test_public_archive_metadata_and_local_match_are_aggregate_only(tmp_path: Path) -> None:
    payload = {
        "data": {
            "id": 1,
            "identifier": "USN.26117989",
            "latestVersion": {
                "versionNumber": 1,
                "versionMinorNumber": 0,
                "publicationDate": "2025-05-26",
                "license": {"name": "CC BY 4.0", "uri": "https://creativecommons.org/licenses/by/4.0/"},
                "files": [
                    {"dataFile": {"filename": "23_FFI_P101_T00003.zip", "filesize": 3, "md5": "900150983cd24fb0d6963f7d28e17f72", "id": 1}},
                    {"dataFile": {"filename": "ReadMe.txt", "filesize": 5, "md5": "ignored", "id": 2}},
                ],
            },
        }
    }
    metadata = _public_archive_metadata(payload)
    assert metadata["archive_count"] == 1
    assert metadata["archives"][0]["filename"] == "23_FFI_P101_T00003.zip"
    archive = tmp_path / "23_FFI_P101_T00003.zip"
    archive.write_bytes(b"abc")
    checked = compare_local_archives(metadata, tmp_path)
    assert checked["all_public_md5_match"] is True
    assert checked["matched_count"] == 1
