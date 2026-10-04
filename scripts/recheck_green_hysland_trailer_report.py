"""Recheck the public Green Hysland historical KPI report.

The public report is generated on demand.  This check keeps only a digest and
the extracted row-level boundary: it verifies that the tube-trailer operating
context is present, while recording that the HRS provisional section contains
no station-to-vehicle transaction trace.  The downloaded PDF is never stored
in the repository.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import sys
from urllib.request import Request, urlopen


REPORT_URL = (
    "https://enagasrenovable.idboxrt.com/reports/api/ReportViewer/"
    "exportOpenPermalink/46?op=KvUKXujUk&sg=3"
)

REQUIRED_TRAILER_ROWS = (
    "Tube Trailers - Operation frequency",
    "Tube Trailers - Total storage capacity kg",
    "Tube Trailers - Usable storage capacity kg",
    "Tube Trailers - Storage pressure bar",
    "Tube Trailers - Peak hydrogen charging rate",
)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _fetch() -> tuple[int, str, bytes]:
    request = Request(REPORT_URL, headers={"User-Agent": "hrs-validation-recheck/1.0"})
    with urlopen(request, timeout=120) as response:
        return response.status, response.headers.get("Content-Type", ""), response.read()


def _extract_text(data: bytes) -> tuple[int, str]:
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover - environment diagnostic
        raise RuntimeError("pypdf is required to inspect the public PDF") from exc
    reader = PdfReader(io.BytesIO(data), strict=False)
    pages = [page.extract_text() or "" for page in reader.pages]
    return len(pages), "\n".join(pages)


def recheck() -> dict[str, object]:
    status, content_type, payload = _fetch()
    page_count, text = _extract_text(payload)
    rows = {row: row in text for row in REQUIRED_TRAILER_ROWS}
    trailer_lines = {
        row: next((line.strip() for line in text.splitlines() if line.strip().startswith(row)), None)
        for row in REQUIRED_TRAILER_ROWS
    }
    # The report prints the HRS Provisional field names but no values after
    # them.  This is intentionally kept as a negative boundary, not inferred
    # as a station transaction trace.
    hrs_marker = "HRS Provisional - H2 pressure bar"
    hrs_section = text[text.find(hrs_marker) :] if hrs_marker in text else ""
    hrs_rows = [
        line.strip()
        for line in hrs_section.splitlines()
        if line.strip().startswith("HRS Provisional -")
    ]
    return {
        "schema_version": 1,
        "rechecked_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PUBLIC_GREENHYSLAND_REPORT_RECHECKED",
        "source": {
            "title": "Green Hysland historical data repository report",
            "url": "https://greenhysland.eu/data-collection-system/",
            "report_url": REPORT_URL,
            "publisher": "Green Hysland / Enagás Renovable",
        },
        "download": {
            "http_status": status,
            "content_type": content_type,
            "bytes": len(payload),
            "sha256": _sha256(payload),
            "pdf_pages": page_count,
        },
        "tube_trailer_context": {
            "required_rows_present": rows,
            "all_required_rows_present": all(rows.values()),
            "row_text": trailer_lines,
        },
        "hrs_provisional_boundary": {
            "field_row_count": len(hrs_rows),
            "field_rows": hrs_rows,
            "populated_transaction_values": False,
            "required_missing_channels": [
                "station/dispenser pressure trace",
                "vehicle/receptacle pressure trace",
                "temperature trace",
                "mass-flow or transferred-mass trace",
                "common time base",
            ],
        },
        "eligibility_decision": {
            "component_boundary_context_eligible": True,
            "full_loop_external_holdout_eligible": False,
            "allowed_use": [
                "tube-trailer operating-range context",
                "data-request lead",
                "station inventory and KPI face-validity context",
            ],
            "prohibited_use": [
                "station-to-vehicle full-loop score",
                "controller or protocol validation",
                "post-hoc parameter fitting",
                "site safety-distance validation",
            ],
        },
        "claim_boundary": (
            "The live report verifies public tube-trailer KPI context, but its HRS "
            "provisional section has no populated synchronized transaction trace; "
            "the independent full-loop gate remains open."
        ),
    }


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("research/green_hysland_trailer_report_recheck_2026_10_05.json"),
    )
    args = parser.parse_args()
    report = recheck()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
