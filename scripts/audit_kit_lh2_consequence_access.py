"""Audit the local KIT LH2 consequence archive without opening signal values.

The KIT archive is an acquisition lead for consequence-model validation.  The
stage-1 protocol permits checking the byte-level download and listing archive
members, but it forbids reading pressure, flow, heat-flux or video outcomes
before a stage-2 model/endpoint protocol is frozen.  This audit therefore
records only provenance, hashes, archive-member headers and integrity status.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import tarfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RAW_DIR = ROOT / "data/public_validation/raw/kit_lh2_consequence_1483"
DEFAULT_PROTOCOL = ROOT / "research/kit_lh2_consequence_intake_protocol_2026_10_08.json"
DEFAULT_OUTPUT = ROOT / "research/kit_lh2_consequence_access_audit_2026_10_11.json"


def _hash(path: Path, algorithm: str) -> str:
    digest = hashlib.new(algorithm)
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _member_summary(member: tarfile.TarInfo) -> dict[str, Any]:
    suffix = Path(member.name).suffix.lower()
    if suffix in {".csv", ".tsv", ".txt", ".dat", ".json", ".xlsx", ".xls"}:
        family = "metadata_or_signal_file"
    elif suffix in {".mp4", ".mov", ".avi", ".mkv"}:
        family = "video_outcome_file"
    elif suffix in {".pdf", ".docx", ".md", ".rst"}:
        family = "documentation_file"
    else:
        family = "container_or_other"
    return {
        "name": member.name,
        "type": "directory" if member.isdir() else "file" if member.isfile() else "other",
        "size_bytes": member.size,
        "family_hint": family,
    }


def _scan_members(archive: Path) -> dict[str, Any]:
    members: list[dict[str, Any]] = []
    error: str | None = None
    try:
        with tarfile.open(archive, mode="r:*") as stream:
            for member in stream:
                members.append(_member_summary(member))
    except (tarfile.ReadError, EOFError, OSError) as exc:
        error = f"{type(exc).__name__}: {exc}"
    return {
        "members": members,
        "member_count": len(members),
        "complete": error is None,
        "error": error,
        "values_opened": False,
        "video_outcomes_opened": False,
    }


def audit(raw_dir: Path, protocol_path: Path) -> dict[str, Any]:
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    archive = raw_dir / "archive.tar"
    if not archive.is_file():
        raise FileNotFoundError(f"KIT archive not found: {archive}")

    scan = _scan_members(archive)
    expected = protocol["source"]
    actual_md5 = _hash(archive, "md5")
    actual_sha256 = _hash(archive, "sha256")
    byte_count = archive.stat().st_size
    md5_match = actual_md5.lower() == str(expected["publisher_reported_md5"]).lower()
    integrity_pass = md5_match and scan["complete"]
    return {
        "schema_version": 1,
        "artifact_type": "kit_lh2_consequence_stage1_access_audit",
        "recorded_at": "2026-10-11",
        "frozen_protocol": {
            "artifact": "research/kit_lh2_consequence_intake_protocol_2026_10_08.json",
            "protocol_id": protocol.get("protocol_id"),
            "protocol_status": protocol.get("status"),
            "protocol_sha256": _hash(protocol_path, "sha256"),
        },
        "source": {
            "doi": expected.get("doi"),
            "official_record": expected.get("official_record"),
            "license": expected.get("license"),
            "archive_version": expected.get("archive_version"),
            "publisher_reported_archive_size": expected.get("publisher_reported_archive_size"),
            "publisher_reported_md5": expected.get("publisher_reported_md5"),
        },
        "local_download": {
            "archive_bytes": byte_count,
            "archive_md5": actual_md5,
            "archive_sha256": actual_sha256,
            "md5_matches_publisher": md5_match,
            "archive_member_scan": scan,
        },
        "eligibility_decision": {
            "stage1_integrity_verified": integrity_pass,
            "stage1_inventory_complete": scan["complete"],
            "stage2_eligible": False,
            "claim_supported": False,
            "reason": (
                "The local archive is incomplete or does not match the publisher checksum. "
                "Acquire the exact archive through an authenticated/session-aware route and "
                "re-run checksum verification before any outcome file is opened."
            ),
        },
        "privacy_and_protocol_boundary": {
            "numeric_signal_values_opened": False,
            "video_outcomes_opened": False,
            "raw_rows_committed": False,
            "parameter_fitting_performed": False,
            "member_headers_only": True,
        },
        "claim_boundary": (
            "This artifact documents a failed/incomplete stage-1 access attempt only. "
            "It does not validate a release, dispersion, ignition, heat-flux or overpressure "
            "model, HyRAM, safety distance, station control or SAGA."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW_DIR)
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    result = audit(args.raw_dir.resolve(), args.protocol.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(args.output),
        "stage1_integrity_verified": result["eligibility_decision"]["stage1_integrity_verified"],
        "stage2_eligible": result["eligibility_decision"]["stage2_eligible"],
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
