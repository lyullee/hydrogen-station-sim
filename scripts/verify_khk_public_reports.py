"""Verify access and provenance of the public KHK hydrogen accident PDFs.

The linked reports are downloaded only to the gitignored ``tmp`` directory.  The
repository records URL-level provenance, byte counts, hashes and page counts,
but never republishes the report files or extracted report text.  This makes the
actual-accident evidence auditable without changing KHK's redistribution terms.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


USER_AGENT = "hydrogen-station-sim-khk-provenance/1.0"
DEFAULT_SOURCE = Path("research/khk_hydrogen_station_public_reports_inventory_2026_10_04.json")
DEFAULT_RAW_DIR = Path("tmp/khk_public_reports_2026_10_04")
DEFAULT_OUTPUT = Path("research/khk_public_reports_access_verification_2026_10_04.json")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _filename(index: int, item: dict) -> str:
    code = "_".join(str(code) for code in item.get("incident_codes", []))
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", code or str(index))
    return f"{index:02d}_{safe}.pdf"


def _fetch(url: str, path: Path, *, retries: int = 3) -> dict:
    last_error: str | None = None
    for attempt in range(1, retries + 1):
        try:
            request = Request(url, headers={"User-Agent": USER_AGENT})
            with urlopen(request, timeout=120) as response, path.open("wb") as output:
                output.write(response.read())
                content_type = response.headers.get("content-type", "")
                final_url = response.geturl()
                status = getattr(response, "status", 200)
            return {
                "http_status": int(status),
                "content_type": content_type,
                "final_url": final_url,
                "attempts": attempt,
            }
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            if attempt < retries:
                time.sleep(float(attempt))
    return {"error": last_error or "unknown download error", "attempts": retries}


def _page_count(path: Path) -> int | None:
    try:
        from pypdf import PdfReader

        return len(PdfReader(str(path), strict=False).pages)
    except Exception:
        return None


def verify(source_path: Path, raw_dir: Path) -> dict:
    source = json.loads(source_path.read_text(encoding="utf-8"))
    reports = source.get("accident_reports") or []
    raw_dir.mkdir(parents=True, exist_ok=True)
    records: list[dict] = []
    for index, item in enumerate(reports, start=1):
        path = raw_dir / _filename(index, item)
        response = _fetch(str(item["url"]), path)
        record = {
            "incident_codes": item.get("incident_codes", []),
            "date": item.get("date"),
            "title": item.get("title"),
            "equipment_class": item.get("equipment_class"),
            "url": item.get("url"),
            **response,
        }
        if path.is_file() and path.stat().st_size:
            record.update({
                "bytes": path.stat().st_size,
                "sha256": _sha256(path),
                "pdf_magic": path.read_bytes()[:5] == b"%PDF-",
                "page_count": _page_count(path),
            })
        else:
            record.update({"bytes": 0, "sha256": None, "pdf_magic": False, "page_count": None})
        records.append(record)
    verified = [
        record for record in records
        if record.get("http_status") == 200
        and record.get("content_type", "").lower().startswith("application/pdf")
        and record.get("bytes", 0) > 0
        and record.get("pdf_magic") is True
        and len(record.get("sha256") or "") == 64
        and record.get("page_count", 0) > 0
    ]
    return {
        "schema_version": 1,
        "status": "public_khk_accident_report_access_verified" if len(verified) == len(reports) else "partial_public_khk_accident_report_access",
        "source_inventory": str(source_path).replace("\\", "/"),
        "source_page": source.get("source_page", {}),
        "raw_directory": str(raw_dir).replace("\\", "/"),
        "report_count": len(reports),
        "verified_report_count": len(verified),
        "records": records,
        "rights_boundary": "Report PDFs remain local and gitignored. Only URL provenance, hashes, byte counts and page counts are committed; report text and files are not redistributed.",
        "claim_boundary": "This verifies access and provenance of public accident reports for qualitative scenario grounding. It does not provide synchronized process traces, event frequencies, causal inference or physics validation.",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    result = verify(args.source, args.raw_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "report_count": result["report_count"], "verified_report_count": result["verified_report_count"], "output": str(args.output)}, ensure_ascii=False))
    return 0 if result["status"] == "public_khk_accident_report_access_verified" else 1


if __name__ == "__main__":
    raise SystemExit(main())
