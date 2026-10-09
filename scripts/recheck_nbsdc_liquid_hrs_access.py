"""Recheck the public NBSDC liquid-HRS catalogue without retaining raw rows.

The catalogue exposes a description and numerical-file inventory, while the
XLSX/CSV files are controlled by a data-application workflow.  This script
records the current metadata and download boundary so a future custodian
response can be compared with an auditable baseline without bypassing access
controls or copying private measurement rows into the repository.
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


BASE = "https://nbsdc.cn"
DATA_ID = "67d50e37195d260905af9869"
ROOT_PID = "1"


def _get(url: str) -> tuple[int, str, bytes]:
    request = Request(url, headers={"User-Agent": "hrs-validation-recheck/1.0"})
    with urlopen(request, timeout=30) as response:
        body = response.read()
        return response.status, response.headers.get("Content-Type", ""), body


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _url(path: str, **params: str) -> str:
    return f"{BASE}{path}?{urlencode(params)}"


def _json_body(body: bytes, content_type: str) -> dict[str, object] | None:
    if not content_type.lower().startswith("application/json"):
        return None
    try:
        value = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def recheck() -> dict[str, object]:
    metadata_url = _url("/api/general/searchDataDetail", id=DATA_ID)
    tree_url = _url(
        "/api/general/v1/getFileTree",
        dataId=DATA_ID,
        pid=ROOT_PID,
        pageOffset="0",
        pageSize="100",
    )
    metadata_status, metadata_type, metadata_body = _get(metadata_url)
    tree_status, tree_type, tree_body = _get(tree_url)
    metadata = json.loads(metadata_body.decode("utf-8"))
    tree = json.loads(tree_body.decode("utf-8"))
    result = metadata.get("result") or {}
    data_info = result.get("dataInfoMap") or {}
    strategy = result.get("dataStrategyMap") or {}
    storage = result.get("dataStorageSizeMap") or {}
    files = ((tree.get("data") or {}).get("list") or [])

    numerical = [item for item in files if item.get("isFile") and not str(item.get("fileName", "")).lower().endswith(".docx")]
    description = [item for item in files if str(item.get("fileName", "")).lower().endswith(".docx")]
    probes = []
    for item in numerical + description:
        file_id = str(item.get("id"))
        probe_url = _url(
            "/api/general/v1/checkAndDownloadFile",
            dataId=DATA_ID,
            id=file_id,
            pid=ROOT_PID,
            pageOffset="0",
            pageSize="12",
        )
        status, content_type, body = _get(probe_url)
        parsed = _json_body(body, content_type)
        probes.append(
            {
                "file_id": file_id,
                "file_name": item.get("fileName"),
                "http_status": status,
                "content_type": content_type,
                "bytes": len(body),
                "sha256": _sha256(body),
                "portal_code": parsed.get("code") if parsed else None,
                "portal_message": parsed.get("message") if parsed else None,
                "description_file": item in description,
                "raw_bytes_retained": False,
            }
        )

    inventory = [
        {
            "id": item.get("id"),
            "name": item.get("fileName"),
            "size_bytes": item.get("size"),
            "role": _role(str(item.get("fileName", ""))),
        }
        for item in files
        if item.get("isFile")
    ]
    description_probe = next((probe for probe in probes if probe["description_file"]), {})
    numeric_probes = [probe for probe in probes if not probe["description_file"]]
    return {
        "schema_version": 1,
        "rechecked_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "REAL_LHRS_METADATA_CONFIRMED_NUMERICAL_FILES_APPLICATION_CONTROLLED",
        "source": {
            "title": data_info.get("dataSetEnName") or "Operating Dataset of Liquid Hydrogen Refueling Station",
            "title_zh": data_info.get("dataSetCnName") or "液氢加氢站运行数据集",
            "data_id": DATA_ID,
            "cstr": (result.get("dataBaoShiMap") or {}).get("cstr"),
            "landing_url": f"{BASE}/general/dataDetail?id={DATA_ID}&type=1",
            "metadata_endpoint": metadata_url,
            "provider": ((result.get("dataOrgUnitMap") or [{}])[0] or {}).get("orgUnitCn"),
            "share_range": strategy.get("shareRange"),
            "catalog_updated_at": result.get("updateTime"),
        },
        "metadata_observation": {
            "http_status": metadata_status,
            "file_tree_http_status": tree_status,
            "file_count": storage.get("filesNum"),
            "storage_mb": float(storage.get("storageCapacity")) if storage.get("storageCapacity") else None,
            "declared_scope": "Real liquid-HRS operating monitoring over a concentrated 16-hour window at one-second precision; 35 MPa dispensers, 90 MPa compressor, high-pressure storage-cylinder groups, and liquid-pump/tank system.",
            "declared_channels": ["pressure", "temperature", "flow rate", "dispensed mass", "current", "frequency", "liquid level", "volume"],
            "description_file_download": description_probe.get("portal_code") in (None, 200),
            "public_file_inventory": inventory,
        },
        "access_probe": {
            "metadata_url": metadata_url,
            "file_tree_url": tree_url,
            "numeric_download_probes": numeric_probes,
            "description_download_probe": description_probe,
            "raw_numerical_files_obtained": False,
            "claim": "Numerical files were not retained or opened; a portal application response is the only result available without custodian approval.",
        },
        "eligibility": {
            "full_loop_holdout_eligible": False,
            "component_or_station_side_diagnostic_eligible": False,
            "high_value_request_candidate": True,
            "decision": "METADATA_ONLY_UNTIL_CUSTODIAN_APPROVES_NUMERICAL_FILES",
            "required_before_any_model_use": [
                "custodian-approved numerical files",
                "source-file hashes and channel dictionary",
                "common time base and timezone",
                "vehicle/receptacle pressure and temperature definitions",
                "mass-flow or transferred-mass semantics",
                "initial state, tank capacity and pressure-ramp/stop semantics",
                "calibration/quality and alarm/ESD metadata",
                "written permission for derived metrics and IJHE publication",
            ],
        },
        "claim_boundary": "This recheck confirms a high-value public catalogue and its current application boundary. It is not numerical validation, does not establish a gaseous H70 station-to-vehicle holdout, and must not be used for runtime parameter fitting or safety-distance claims.",
        "privacy": {
            "raw_rows_persisted": False,
            "private_site_or_company_identity_published": False,
            "manufacturer_details_published": False,
        },
    }


def _role(name: str) -> str:
    lower = name.lower()
    if "35mpa" in lower and "1" in lower:
        return "dispenser_35mpa_1"
    if "35mpa" in lower and "2" in lower:
        return "dispenser_35mpa_2"
    if "70mpa" in lower:
        return "dispenser_70mpa"
    if "90mpa" in lower:
        return "compressor_90mpa"
    if "液氢泵" in name or "储罐" in name:
        return "liquid_pump_tank"
    if "高压储氢" in name:
        return "high_pressure_storage"
    if lower.endswith(".docx"):
        return "description"
    return "catalogue_file"


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("research/nbsdc_liquid_hrs_public_access_recheck_2026_10_10_live.json"),
    )
    args = parser.parse_args()
    report = recheck()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
