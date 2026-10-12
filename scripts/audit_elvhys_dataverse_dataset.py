"""Build a privacy-bounded inventory of the public ELVHYS 4.2 dataset.

The Dataverse record contains public, actual-cryogenic-hydrogen experiment
files.  This audit stores only aggregate metadata, file-family counts and the
published test-plan classification.  Raw rows and source filenames are never
committed and the dataset is not promoted to a station or runtime gate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PERSISTENT_ID = "doi:10.18710/JXJP0H"
API_URL = (
    "https://dataverse.no/api/datasets/:persistentId/?persistentId="
    + PERSISTENT_ID
)
LANDING_URL = "https://dataverse.no/dataset.xhtml?persistentId=" + PERSISTENT_ID


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _fetch() -> dict[str, Any]:
    request = urllib.request.Request(
        API_URL, headers={"User-Agent": "h2station-evidence-audit"}
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        value = json.load(response)
    if not isinstance(value, dict) or value.get("status") != "OK":
        raise ValueError("Dataverse API did not return a successful object")
    return value


def _test_plan(readme: str) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for line in readme.splitlines():
        match = re.match(r"\s*(\d+)\s+(.+?)\s*$", line)
        if not match:
            continue
        test_id = int(match.group(1))
        if test_id < 1 or test_id > 48:
            continue
        text = match.group(2)
        if "Pressure Peaking" in text:
            kind = "pressure_peaking"
        elif "Ignited" in text:
            kind = "ignition"
        elif "Vertical" in text:
            kind = "dispersion_vertical"
        elif "Dispersion Horizontal" in text:
            kind = "dispersion_horizontal"
        else:
            continue
        rows.append(
            {
                "test_id": test_id,
                "kind": kind,
                "invalid_or_commissioning": "Invalid test" in text,
            }
        )
    # Test rows are public planning metadata; retain only aggregate counts.
    kinds = {kind: 0 for kind in (
        "dispersion_horizontal", "pressure_peaking", "ignition", "dispersion_vertical"
    )}
    invalid = 0
    for row in rows:
        kinds[row["kind"]] += 1
        invalid += int(row["invalid_or_commissioning"])
    return {
        "published_test_plan_count": 48,
        "test_plan_rows_parsed": len(rows),
        "test_plan_type_counts": kinds,
        "invalid_or_commissioning_count": invalid,
        "valid_or_usable_plan_count": max(0, len(rows) - invalid),
    }


def audit(record: dict[str, Any], readme_path: Path) -> dict[str, Any]:
    data = record.get("data") or {}
    version = data.get("latestVersion") or {}
    files = [item.get("dataFile") or {} for item in version.get("files") or []]
    if not files:
        raise ValueError("Dataverse record has no files")
    family_counts = {
        "concentration": 0,
        "flow_rate": 0,
        "miscellaneous_weather": 0,
        "pressure": 0,
        "temperature": 0,
        "metadata_or_readme": 0,
    }
    case_ids: set[int] = set()
    manifest_rows: list[str] = []
    for file in files:
        name = str(file.get("filename") or "")
        upper = name.upper()
        family = None
        for token, label in (
            ("CONC", "concentration"),
            ("FLMT", "flow_rate"),
            ("MISC", "miscellaneous_weather"),
            ("PRES", "pressure"),
            ("TEMP", "temperature"),
        ):
            if token in upper:
                family = label
                break
        if family is None:
            family = "metadata_or_readme"
        family_counts[family] += 1
        match = re.search(r"ELE402HSE0*(\d+)", name)
        if match:
            case_ids.add(int(match.group(1)))
        manifest_rows.append(
            f"{file.get('id')}|{file.get('filesize')}|{file.get('md5')}"
        )
    readme_bytes = readme_path.read_bytes()
    readme = readme_bytes.decode("utf-8", errors="replace")
    if "cryogenic hydrogen" not in readme.lower() or "48 tests" not in readme:
        raise ValueError("ELVHYS README identity checks failed")
    source = {
        "persistent_id": PERSISTENT_ID,
        "doi": "10.18710/JXJP0H",
        "api_url": API_URL,
        "landing_url": LANDING_URL,
        "title": str(version.get("metadataBlocks", {}).get("citation", {}).get("fields", [{}])[0].get("value") or "ELVHYS 4.2"),
        "license": str((version.get("license") or {}).get("name") or ""),
        "publication_date": version.get("publicationDate"),
        "version": f"{version.get('versionNumber')}.{version.get('versionMinorNumber')}",
    }
    plan = _test_plan(readme)
    schema_pass = (
        source["doi"] == "10.18710/JXJP0H"
        and source["license"] == "CC0 1.0"
        and len(files) == 198
        and family_counts["concentration"] == 40
        and family_counts["pressure"] == 40
        and family_counts["temperature"] == 40
        and family_counts["flow_rate"] == 35
        and plan["published_test_plan_count"] == 48
    )
    return {
        "schema_version": 1,
        "artifact_type": "public_elvhys_4_2_actual_cryogenic_hydrogen_inventory",
        "recorded_at": "2026-10-12",
        "source": source,
        "dataset_scope": {
            "actual_cryogenic_hydrogen": True,
            "experimental_campaign": "ELVHYS WP4.2",
            "transfer_connection_space_volume_m3": 1.0,
            "data_file_count": len(files),
            "case_id_count_with_public_data": len(case_ids),
            "case_ids_with_public_data_min_max": [min(case_ids), max(case_ids)],
            "file_family_counts": family_counts,
            "measured_channel_families": [
                "hydrogen concentration", "pressure", "temperature",
                "release flow rate", "weather/ventilation", "flame/ignition",
            ],
            "sampling_context": "mostly 20 Hz; selected pressure-peaking and ignition channels at higher rates",
            **plan,
        },
        "integrity": {
            "api_file_manifest_sha256": hashlib.sha256(
                "\n".join(sorted(manifest_rows)).encode("utf-8")
            ).hexdigest(),
            "readme_sha256": _sha256(readme_path),
            "readme_bytes": len(readme_bytes),
            "raw_rows_committed": False,
            "source_filenames_committed": False,
        },
        "eligibility": {
            "schema_screen_pass": schema_pass,
            "independent_actual_cryogenic_hydrogen_component_candidate": schema_pass,
            "dispersion_candidate": schema_pass,
            "pressure_peaking_candidate": schema_pass,
            "ignition_consequence_candidate": schema_pass,
            "station_to_vehicle_full_loop": False,
            "runtime_parameter_application": False,
            "validation_gate_promoted": False,
        },
        "next_action": "Freeze a pre-access channel/unit protocol and reserve disjoint test IDs before numerical outcome scoring.",
        "claim_boundary": (
            "Public ELVHYS 4.2 actual-cryogenic-hydrogen component evidence only. "
            "It does not validate the HRS station twin, vehicle fueling, ESD logic, "
            "site-specific consequence distances, or runtime parameters."
        ),
    }


def markdown(result: dict[str, Any]) -> str:
    scope = result["dataset_scope"]
    eligibility = result["eligibility"]
    lines = [
        "# ELVHYS 4.2 public actual-cryogenic-hydrogen dataset inventory",
        "",
        f"- DOI: `https://doi.org/{result['source']['doi']}`",
        f"- License: `{result['source']['license']}`",
        f"- Planned tests: `{scope['published_test_plan_count']}`",
        f"- Public data case groups: `{scope['case_id_count_with_public_data']}`",
        f"- Data files: `{scope['data_file_count']}`",
        f"- Schema screen: **{'PASS' if eligibility['schema_screen_pass'] else 'FAIL'}**",
        "- Raw rows committed: **false**",
        "",
        "The public campaign contains actual cryogenic-hydrogen dispersion, pressure-peaking and ignition measurements in a 1 m³ transfer-connection space. Only aggregate metadata and a bounded test-plan classification are retained here.",
        "",
        "## Boundary",
        "",
        result["claim_boundary"],
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--readme", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "research/elvhys_4_2_public_dataset_inventory_2026_10_12.json")
    parser.add_argument("--markdown", type=Path, default=ROOT / "research/ELVHYS_4_2_PUBLIC_DATASET_INVENTORY_2026_10_12.md")
    args = parser.parse_args()
    result = audit(_fetch(), args.readme.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.markdown.write_text(markdown(result), encoding="utf-8")
    print(json.dumps({"output": str(args.output), "schema_screen_pass": result["eligibility"]["schema_screen_pass"], "data_file_count": result["dataset_scope"]["data_file_count"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()

