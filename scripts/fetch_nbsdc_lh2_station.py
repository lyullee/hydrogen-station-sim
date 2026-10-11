"""Fetch the publicly shared NBSDC liquid-hydrogen station package.

The protocol is read before any numerical file is requested.  Raw files stay
under the ignored ``data/`` tree; the committed result contains only hashes,
sizes and eligibility metadata.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "research" / "nbsdc_lh2_station_intake_protocol_2026_10_12.json"
DEFAULT_OUTPUT = ROOT / "research" / "nbsdc_lh2_station_intake_result_2026_10_12.json"
RAW_DIR = ROOT / "data" / "public_validation" / "raw" / "nbsdc_lh2_station"
BASE_URL = "https://nbsdc.cn/api/general/v1/checkAndDownloadFile"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fetch_file(entry: dict[str, object], dataset_id: str) -> dict[str, object]:
    tree_id = int(entry["tree_id"])
    # The record's API uses a stable UUID per file.  Resolve it from the public
    # tree first rather than deriving it from the numeric tree id.
    tree_url = (
        "https://nbsdc.cn/api/general/v1/getFileTree?"
        + urlencode({"dataId": dataset_id, "pid": 1, "pageOffset": 0, "pageSize": 100})
    )
    tree_request = Request(
        tree_url,
        headers={"Accept": "application/json", "User-Agent": "HRS-sim-public-intake/1.0"},
    )
    with urlopen(tree_request, timeout=60) as response:
        tree = json.loads(response.read().decode("utf-8"))
    matches = [item for item in (tree.get("data", {}).get("list") or []) if item.get("treeId") == tree_id]
    if len(matches) != 1:
        raise RuntimeError(f"tree id {tree_id} did not resolve uniquely")
    query = urlencode(
        {
            "dataId": dataset_id,
            "id": matches[0]["id"],
            "pid": 1,
            "pageOffset": 0,
            "pageSize": 100,
        }
    )
    request = Request(
        f"{BASE_URL}?{query}",
        headers={
            "Accept": "*/*",
            "Referer": f"https://nbsdc.cn/general/dataDetail?id={dataset_id}&type=1",
            "User-Agent": "HRS-sim-public-intake/1.0",
        },
    )
    with urlopen(request, timeout=180) as response:
        content_type = response.headers.get("Content-Type", "")
        payload = response.read()
    if "application/json" in content_type:
        try:
            refusal = json.loads(payload.decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError):
            refusal = {"code": None, "message": "unparseable access response"}
        return {
            "tree_id": tree_id,
            "name": entry["name"],
            "role": entry["role"],
            "access_status": "access_denied",
            "http_response_code": refusal.get("code"),
            "access_message": str(refusal.get("message") or ""),
            "catalogue_bytes": entry["bytes"],
            "raw_rows_persisted_in_result": False,
        }
    target = RAW_DIR / f"{entry['role']}__{entry['name']}"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(payload)
    return {
        "tree_id": tree_id,
        "name": entry["name"],
        "role": entry["role"],
        "access_status": "downloaded",
        "path": str(target.relative_to(ROOT)).replace("\\", "/"),
        "bytes": len(payload),
        "sha256": sha256(target),
        "catalogue_bytes": entry["bytes"],
        "byte_count_matches_catalogue": len(payload) == entry["bytes"],
        "content_type": content_type,
        "raw_rows_persisted_in_result": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    if protocol.get("status") != "frozen_before_numerical_access":
        raise SystemExit("protocol is not frozen before numerical access")
    records = [fetch_file(entry, protocol["source"]["dataset_id"]) for entry in protocol["files"]]
    aggregate = {
        "file_count": len(records),
        "downloaded_count": sum(record.get("access_status") == "downloaded" for record in records),
        "access_denied_count": sum(record.get("access_status") == "access_denied" for record in records),
        "all_files_downloaded": all(record.get("access_status") == "downloaded" for record in records),
        "catalogue_byte_mismatch_count": sum(
            record.get("access_status") == "downloaded"
            and not bool(record.get("byte_count_matches_catalogue"))
            for record in records
        ),
        "raw_rows_persisted": False,
        "runtime_parameter_changed": False,
        "claim_supported": False,
    }
    if aggregate["access_denied_count"]:
        status = "metadata_accessed_numerical_files_access_denied"
    elif aggregate["all_files_downloaded"]:
        status = "all_catalogued_files_downloaded"
    else:
        status = "partial_public_file_access"
    result = {
        "schema_version": 1,
        "artifact_type": "public_nbsdc_lh2_station_intake_result",
        "status": status,
        "protocol": str(PROTOCOL.relative_to(ROOT)).replace("\\", "/"),
        "protocol_sha256": sha256(PROTOCOL),
        "source": protocol["source"],
        "files": records,
        "aggregate": aggregate,
        "claim_boundary": protocol["evaluation"]["claim_limit"],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result["aggregate"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
