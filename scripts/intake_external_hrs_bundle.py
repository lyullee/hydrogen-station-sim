"""Hash an external HRS data package without inspecting numerical values.

The command is deliberately metadata-only: it enumerates files and hashes
bytes, but never opens CSV/XLSX/Parquet cells or parses archive members. This
allows a received package to be quarantined before a prospective evaluation
protocol reads outcomes.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Iterable


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _files(input_path: Path) -> list[Path]:
    if input_path.is_file():
        return [input_path]
    if input_path.is_dir():
        return sorted(path for path in input_path.rglob("*") if path.is_file())
    raise FileNotFoundError(input_path)


def build_manifest(input_path: Path, protocol_path: Path) -> dict:
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    if protocol.get("status") != "prospective_intake_contract":
        raise ValueError("intake protocol status is not prospective_intake_contract")
    if protocol.get("outcomes_accessed_before_freeze") is not False:
        raise ValueError("intake protocol does not confirm pre-outcome freeze")
    paths = _files(input_path)
    if not paths:
        raise ValueError("input package contains no files")
    records = []
    root = input_path if input_path.is_dir() else input_path.parent
    for path in paths:
        records.append(
            {
                "relative_path": str(path.relative_to(root)).replace("\\", "/"),
                "bytes": path.stat().st_size,
                "sha256": _sha256(path),
            }
        )
    return {
        "schema_version": 1,
        "manifest_type": "external_hrs_metadata_only_intake",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_path": str(input_path),
        "protocol_path": str(protocol_path),
        "protocol_sha256": _sha256(protocol_path),
        "numerical_values_inspected": False,
        "archive_members_parsed": False,
        "file_count": len(records),
        "files": records,
        "claim_boundary": protocol["claim_boundary"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path, help="Quarantined file or directory")
    parser.add_argument(
        "--protocol",
        type=Path,
        default=Path("research/external_hrs_intake_protocol.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/public_validation/results/external_hrs_intake/manifest.json"),
    )
    args = parser.parse_args()
    manifest = build_manifest(args.input, args.protocol)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
