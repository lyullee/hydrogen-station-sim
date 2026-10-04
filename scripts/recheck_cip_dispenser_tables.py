"""Recheck the public CIP hydrogen-dispenser table artifacts.

The article exposes four small CSV ZIP files.  This check verifies that the
links still return the same table payloads and records the file-level shape.
It deliberately does not treat endpoint tables as synchronized validation
traces or copy the third-party bytes into the repository.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import csv
import hashlib
import io
import json
from pathlib import Path
import sys
from urllib.request import Request, urlopen
import zipfile


BASE = "https://esst.cip.com.cn/article/2020/2095-4239/2095-4239-2020-9-3-702"
EXPECTED = {
    "T1": {
        "sha256": "b98ac67fcf751801a86228dd8ee8779e50c2832ba5a78ed3c187654dc7725ac3",
        "description": "35 MPa initial-condition table",
    },
    "T2": {
        "sha256": "06beb809e4021e3aee9e641e07ac4cdef98a9ae71a2abfa2ab7009a8ae28ecd0",
        "description": "35 MPa final-condition table",
    },
    "T3": {
        "sha256": "33d2eeddd627260044b1be28f209372bd4283058afd5837ec95a029ce6bdde02",
        "description": "70 MPa initial-condition table",
    },
    "T4": {
        "sha256": "44c6fc612715ef018ecde9e4a734eee86fa75640b5b91614e21b2bd035537a2e",
        "description": "70 MPa final-condition table",
    },
}


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _fetch(url: str) -> tuple[int, str, bytes]:
    request = Request(url, headers={"User-Agent": "hrs-validation-recheck/1.0"})
    with urlopen(request, timeout=60) as response:
        return response.status, response.headers.get("Content-Type", ""), response.read()


def _inspect_zip(data: bytes, table: str) -> dict[str, object]:
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        names = archive.namelist()
        expected_member = f"{table}.csv"
        if names != [expected_member]:
            raise ValueError(f"unexpected {table} members: {names!r}")
        raw = archive.read(expected_member)
    text = raw.decode("gb18030")
    rows = list(csv.reader(io.StringIO(text)))
    columns = [cell.strip() for cell in rows[1]] if len(rows) >= 2 else []
    return {
        "members": names,
        "csv_bytes": len(raw),
        "rows": len(rows),
        "columns": columns,
        # The endpoint tables contain a single duration field (加注时间), not
        # a sampled time axis.  Only a dedicated Time/时间 axis counts here.
        "has_time_axis": any(
            column.strip().lower() in {"time", "timestamp", "时间"}
            for column in columns
        ),
        "table_text_sha256": _sha256(raw),
    }


def recheck() -> dict[str, object]:
    tables = []
    for table, expected in EXPECTED.items():
        url = f"{BASE}/{table}.csv.zip"
        status, content_type, payload = _fetch(url)
        digest = _sha256(payload)
        inspection = _inspect_zip(payload, table)
        tables.append(
            {
                "table": table,
                "url": url,
                "http_status": status,
                "content_type": content_type,
                "download_bytes": len(payload),
                "sha256": digest,
                "expected_sha256": expected["sha256"],
                "sha256_matches_expected": digest == expected["sha256"],
                "description": expected["description"],
                "inspection": inspection,
            }
        )
    return {
        "schema_version": 1,
        "rechecked_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PUBLIC_ENDPOINT_TABLES_RECHECKED",
        "source": {
            "title": "35 MPa/70 MPa hydrogen dispenser refuelling performance evaluation",
            "doi": "10.19799/j.cnki.2095-4239.2020.0049",
            "article_url": f"{BASE}.shtml",
            "publisher": "Energy Storage Science and Technology",
        },
        "tables": tables,
        "eligibility_decision": {
            "public_endpoint_tables": True,
            "full_loop_external_holdout_eligible": False,
            "reason": "All four public artifacts are endpoint tables with no synchronized time column or raw station-to-vehicle pressure-temperature-mass-flow trace.",
            "allowed_use": ["contextual operating-range check", "data-request lead"],
            "prohibited_use": ["full-loop holdout score", "post-hoc parameter fitting", "site safety-distance validation"],
        },
        "claim_boundary": "The live URLs and byte-level payloads are reproducibly verified, but the source remains endpoint-only evidence and does not close the independent full-loop gate.",
    }


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("research/cip_2020_live_download_recheck_2026_10_05.json"),
    )
    args = parser.parse_args()
    report = recheck()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
