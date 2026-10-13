"""Record the public metadata and download boundary for the NBSDC LH2 HRS dataset.

The catalog exposes file metadata without authentication, but the raw files are
application-gated.  This script records that boundary without downloading or
storing any operational rows.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen


BASE_URL = "https://www.nbsdc.cn"
DATA_ID = "67d50e37195d260905af9869"
ROOT_ENDPOINT = f"{BASE_URL}/api/general/v1/getFileTree"
DOWNLOAD_ENDPOINT = f"{BASE_URL}/api/general/v1/checkAndDownloadFile"


def get_json(url: str) -> dict:
    request = Request(url, headers={"User-Agent": "hydrogen-station-sim-access-audit/1.0"})
    with urlopen(request, timeout=30) as response:  # noqa: S310 - fixed HTTPS endpoint
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("research/nbsdc_lh2_station_access_recheck_2026_10_14.json"),
    )
    args = parser.parse_args()

    root_query = urlencode({"dataId": DATA_ID, "pid": 0, "pageOffset": 0, "pageSize": 100})
    root = get_json(f"{ROOT_ENDPOINT}?{root_query}")
    root_item = root["data"]["list"][0]

    files_query = urlencode(
        {"dataId": DATA_ID, "pid": root_item["treeId"], "pageOffset": 0, "pageSize": 100}
    )
    files = get_json(f"{ROOT_ENDPOINT}?{files_query}")
    file_items = files["data"]["list"]
    first_file = next(item for item in file_items if item["isFile"])

    download_query = urlencode(
        {
            "dataId": DATA_ID,
            "id": first_file["id"],
            "pid": first_file["pid"],
            "pageOffset": 0,
            "pageSize": 12,
        }
    )
    request = Request(
        f"{DOWNLOAD_ENDPOINT}?{download_query}",
        headers={"User-Agent": "hydrogen-station-sim-access-audit/1.0"},
    )
    with urlopen(request, timeout=30) as response:  # noqa: S310 - fixed HTTPS endpoint
        content_type = response.headers.get("Content-Type", "")
        body = response.read()
    download_json = json.loads(body.decode("utf-8")) if "json" in content_type else None

    artifact = {
        "schema_version": 1,
        "artifact_type": "public_dataset_access_boundary_recheck",
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "source": {
            "catalog_url": "https://nbsdc.cn/general/dataDetail?id=67d50e37195d260905af9869&type=1",
            "dataset_id": DATA_ID,
            "dataset_title": root_item["fileName"],
            "license_or_access_note": "Catalog metadata is public; raw files require a data application.",
        },
        "catalog": {
            "root_endpoint": f"{ROOT_ENDPOINT}?{root_query}",
            "file_endpoint": f"{ROOT_ENDPOINT}?{files_query}",
            "root_status": root.get("code"),
            "file_status": files.get("code"),
            "file_count": len(file_items),
            "files": [
                {
                    "name": item["fileName"],
                    "size_bytes": item.get("size"),
                    "id": item.get("id"),
                    "tree_id": item.get("treeId"),
                }
                for item in file_items
            ],
        },
        "download_probe": {
            "endpoint": f"{DOWNLOAD_ENDPOINT}?{download_query}",
            "content_type": content_type,
            "response": download_json,
            "raw_rows_downloaded": False,
        },
        "eligibility": {
            "actual_station_operational_channels_described": True,
            "metadata_file_inventory_visible": True,
            "raw_rows_rights_cleared_and_downloadable_without_application": False,
            "independent_validation_eligible": False,
            "runtime_parameter_application": False,
        },
        "decision": "ACCESS_BOUNDARY_ONLY",
        "next_action": "Obtain custodian-approved raw files and reuse conditions, then freeze a pre-access protocol before numerical inspection.",
        "claim_boundary": "This recheck proves public catalog metadata and an application-gated download boundary only; it does not validate the digital twin or any runtime parameter.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    # PowerShell on Windows may expose a legacy code page; keep stdout portable.
    print(json.dumps(artifact, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
