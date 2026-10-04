"""Recheck the public NBSDC HRS catalog without downloading gated data files.

The NBSDC catalog exposes metadata and a file tree for the Beijing Winter
Olympics HRS operational archive, while the raw workbooks require a data
application.  This script records that boundary so a stale search result
cannot be mistaken for an independent validation holdout.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
from urllib.parse import urlencode
from urllib.request import Request, urlopen


BASE = "https://www.nbsdc.cn"
DATA_ID = "64edfc52bb16e0300cd4dd38"
RAW_IDS = [
    "641874c7e39c3b0b8e3274a8",
    "641874c7e39c3b0b8e3274a9",
    "641874c7e39c3b0b8e3274aa",
]


def _get(url: str) -> tuple[int, str, bytes]:
    request = Request(url, headers={"User-Agent": "hrs-validation-recheck/1.0"})
    with urlopen(request, timeout=30) as response:
        body = response.read()
        return response.status, response.headers.get("Content-Type", ""), body


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _url(path: str, **params: str) -> str:
    return f"{BASE}{path}?{urlencode(params)}"


def recheck() -> dict[str, object]:
    metadata_url = _url("/api/general/searchDataDetail", id=DATA_ID)
    tree_url = _url(
        "/api/general/v1/getFileTree",
        dataId=DATA_ID,
        pid="11",
        pageOffset="0",
        pageSize="50",
    )
    metadata_status, metadata_type, metadata_body = _get(metadata_url)
    tree_status, tree_type, tree_body = _get(tree_url)
    metadata = json.loads(metadata_body.decode("utf-8"))
    tree = json.loads(tree_body.decode("utf-8"))
    files = (tree.get("data") or {}).get("list") or []

    raw_probes = []
    for file_id in RAW_IDS:
        probe_url = _url(
            "/api/general/v1/checkAndDownloadFile",
            dataId=DATA_ID,
            id=file_id,
            pid="11",
            pageOffset="0",
            pageSize="20",
        )
        status, content_type, body = _get(probe_url)
        raw_probes.append(
            {
                "file_id": file_id,
                "url": probe_url,
                "http_status": status,
                "content_type": content_type,
                "bytes": len(body),
                "sha256": _sha256(body),
                "response": json.loads(body.decode("utf-8"))
                if content_type.lower().startswith("application/json")
                else None,
            }
        )

    data_result = (metadata.get("result") or {})
    return {
        "schema_version": 1,
        "rechecked_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "ACCESS_REQUEST_ONLY_REAL_HRS_CANDIDATE",
        "source": {
            "title": "Operational Data List of Hydrogen Refueling Stations for Beijing Winter Olympics",
            "cstr": (data_result.get("dataBaoShiMap") or {}).get("cstr"),
            "public_landing": "https://cstr.cn/16666.11.nbsdc.aI3fJrzX",
            "internal_data_id": DATA_ID,
            "share_range": (data_result.get("dataStrategyMap") or {}).get("shareRange"),
            "files_declared": (data_result.get("dataStorageSizeMap") or {}).get("filesNum"),
        },
        "api_evidence": {
            "metadata": {
                "url": metadata_url,
                "http_status": metadata_status,
                "content_type": metadata_type,
                "bytes": len(metadata_body),
                "sha256": _sha256(metadata_body),
            },
            "file_tree": {
                "url": tree_url,
                "http_status": tree_status,
                "content_type": tree_type,
                "bytes": len(tree_body),
                "sha256": _sha256(tree_body),
            },
            "raw_file_probes": raw_probes,
        },
        "public_file_inventory": [
            {
                "id": item.get("id"),
                "file_name": item.get("fileName"),
                "size_bytes": item.get("size"),
                "is_file": item.get("isFile"),
            }
            for item in files
        ],
        "eligibility_decision": {
            "full_loop_public_holdout": False,
            "reason": "Metadata and the three-workbook file tree are public, but raw download probes return the portal's application-required response; no raw row was inspected.",
            "high_value_request_candidate": True,
            "required_before_validation": [
                "approved data access",
                "written reuse terms for derived metrics and journal publication",
                "pre-access protocol and case freeze",
                "file hashes and channel dictionary",
                "quality/calibration and station/vehicle time-base confirmation",
            ],
        },
        "claim_boundary": "This recheck proves a current real-HRS access route and declared file inventory only. It is not numerical validation and does not close the full-loop gate.",
    }


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("research/nbsdc_winter_olympics_access_recheck_2026_10_05.json"),
    )
    args = parser.parse_args()
    report = recheck()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
