"""Inventory the public Grune/Sempert ventilation workbooks.

This is a provenance and measurement-coverage inventory, not a model
validation runner.  It deliberately reports measured spatial fields without
comparing them with a post-access model output.  The result can therefore be
used to reproduce the available consequence-evidence boundary without
promoting a confined-space dataset to a full HRS validation claim.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from h2station.public_validation import read_grune_ventilation_workbook


SOURCE_FILES = {
    "HTE2440PS000MIXED_300321.pdf": {
        "bytes": 706086,
        "md5": "d4b59189dd4017c695cc652f4f572128",
    },
    "HTE2440PS001MIXED_300321.xlsx": {
        "bytes": 52610,
        "md5": "da176772755b1a2449a76df9e12b9cd3",
    },
    "HTE2440PS002MIXED_300321.xlsx": {
        "bytes": 65696,
        "md5": "20f996be57fc3d8cf7d091d1f982bd75",
    },
    "HTE2440PS003MIXED_300321.xlsx": {
        "bytes": 50590,
        "md5": "953b6a033553288831b1ee02b881dbec",
    },
    "HTE2440PS004MIXED_300321.xlsx": {
        "bytes": 81649,
        "md5": "093d3d8e6ef030615704ee9096d3d84f",
    },
    "HTE2440PS005FLMT00300321.xlsx": {
        "bytes": 26724,
        "md5": "c4b9195a2bb89213eda9aa2ac9e9ec07",
    },
    "HTE2440PS006MIXED_300321.zip": {
        "bytes": 11108400,
        "md5": "ade3911c0df50ee70486153455f4bd12",
    },
}


def _hashes(path: Path) -> dict[str, Any]:
    md5 = hashlib.md5()
    sha256 = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            md5.update(block)
            sha256.update(block)
    return {
        "bytes": path.stat().st_size,
        "md5": md5.hexdigest(),
        "sha256": sha256.hexdigest(),
    }


def _profile_record(profile: Any) -> dict[str, Any]:
    points = list(profile.points)
    average = [
        float(point.concentration_average_pct)
        for point in points
        if point.concentration_average_pct is not None
    ]
    above_4 = [value for value in average if value >= 4.0]
    max_value = max(average) if average else None
    max_locations = [
        {"x_mm": point.x_mm, "y_mm": point.y_mm}
        for point in points
        if point.concentration_average_pct is not None
        and point.concentration_average_pct == max_value
    ]
    return {
        "source_workbook": profile.source_workbook,
        "sheet_name": profile.sheet_name,
        "release_diameter_mm": profile.release_diameter_mm,
        "nominal_release_g_s": profile.nominal_release_g_s,
        "wind_speed_m_s": profile.wind_speed_m_s,
        "wind_mode": profile.wind_mode,
        "point_count": len(points),
        "x_range_mm": [min(point.x_mm for point in points), max(point.x_mm for point in points)],
        "y_range_mm": [min(point.y_mm for point in points), max(point.y_mm for point in points)],
        "average_concentration_min_pct": min(average) if average else None,
        "average_concentration_max_pct": max_value,
        "average_concentration_mean_pct": (sum(average) / len(average)) if average else None,
        "points_at_or_above_4_vol_pct": len(above_4),
        "fraction_at_or_above_4_vol_pct": (len(above_4) / len(average)) if average else None,
        "maximum_average_concentration_locations": max_locations,
        "measured_release_flow_range_g_s": [
            min(point.release_mass_flow_g_s for point in points),
            max(point.release_mass_flow_g_s for point in points),
        ],
    }


def build(raw_directory: Path) -> dict[str, Any]:
    files = []
    for name, expected in SOURCE_FILES.items():
        path = raw_directory / name
        entry: dict[str, Any] = {
            "name": name,
            "expected": expected,
            "present": path.is_file(),
        }
        if path.is_file():
            observed = _hashes(path)
            entry["observed"] = observed
            entry["identity_match"] = (
                observed["bytes"] == expected["bytes"]
                and observed["md5"] == expected["md5"]
            )
        else:
            entry["identity_match"] = False
        files.append(entry)

    profiles: list[dict[str, Any]] = []
    workbook_errors: list[dict[str, str]] = []
    for name in (
        "HTE2440PS001MIXED_300321.xlsx",
        "HTE2440PS002MIXED_300321.xlsx",
        "HTE2440PS003MIXED_300321.xlsx",
        "HTE2440PS004MIXED_300321.xlsx",
    ):
        path = raw_directory / name
        if not path.is_file():
            continue
        try:
            profiles.extend(_profile_record(profile) for profile in read_grune_ventilation_workbook(path))
        except Exception as exc:  # preserve the failure in the reproducibility record
            workbook_errors.append({"workbook": name, "error": str(exc)})

    identity_ok = all(item["identity_match"] for item in files)
    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "completed_provenance_and_measurement_inventory",
        "evidence_role": "confined_space_ventilation_measurement_inventory",
        "claim_boundary": (
            "This artifact inventories measured confined-space hydrogen concentration and flow fields. "
            "It does not compare a digital-twin prediction with the measurements and does not validate "
            "vehicle filling, cascade dispatch, compressor/precooler control, dispenser protocol, SOC, "
            "outdoor HRS dispersion, or full-station safety effectiveness."
        ),
        "source": {
            "title": "Efficiency of mechanical ventilation on H2 dispersion (PS)",
            "doi": "10.5281/zenodo.4668554",
            "record": "https://zenodo.org/records/4668554",
            "license": "CC BY 4.0",
            "files": files,
        },
        "inventory": {
            "source_identity_all_match": identity_ok,
            "workbook_count": 4,
            "profile_count": len(profiles),
            "spatial_point_count": sum(item["point_count"] for item in profiles),
            "workbook_errors": workbook_errors,
            "release_diameters_mm": sorted({item["release_diameter_mm"] for item in profiles}),
            "wind_modes": sorted({item["wind_mode"] for item in profiles}),
            "release_flow_values_g_s": sorted({item["nominal_release_g_s"] for item in profiles}),
            "profiles": profiles,
        },
        "validation_status": {
            "model_comparison_performed": False,
            "numeric_validation_gate_closed": False,
            "full_loop_external_validation_supported": False,
            "next_step": (
                "Freeze a dispersion model and geometry/ventilation assumptions before using these fields "
                "for any confirmatory score; keep this inventory as the pre-analysis data boundary."
            ),
        },
    }


def markdown(result: dict[str, Any]) -> str:
    source = result["source"]
    inventory = result["inventory"]
    validation = result["validation_status"]
    lines = [
        "# Grune/Sempert ventilation dataset inventory",
        "",
        f"Generated: `{result['generated_at']}`",
        "",
        "This is a provenance and measured-field inventory. It is not a model-validation result.",
        "",
        f"- Source: [{source['title']}]({source['record']})",
        f"- DOI: `{source['doi']}`",
        f"- License: `{source['license']}`",
        f"- Source identity all match: **{inventory['source_identity_all_match']}**",
        f"- Profiles: **{inventory['profile_count']}**",
        f"- Spatial points: **{inventory['spatial_point_count']}**",
        f"- Release diameters: `{inventory['release_diameters_mm']}` mm",
        f"- Wind modes: `{', '.join(inventory['wind_modes'])}`",
        f"- Nominal release flows: `{inventory['release_flow_values_g_s']}` g/s",
        "",
        "## Profile coverage",
        "",
        "| Workbook | Sheet | Nozzle (mm) | Flow (g/s) | Wind | Points | Max H₂ (vol%) | Points ≥4 vol% |",
        "|---|---|---:|---:|---|---:|---:|---:|",
    ]
    for profile in inventory["profiles"]:
        lines.append(
            f"| `{profile['source_workbook']}` | `{profile['sheet_name']}` | "
            f"{profile['release_diameter_mm']:.1f} | {profile['nominal_release_g_s']:.3g} | "
            f"{profile['wind_mode']} ({profile['wind_speed_m_s']:.1f} m/s) | "
            f"{profile['point_count']} | {profile['average_concentration_max_pct']:.3f} | "
            f"{profile['points_at_or_above_4_vol_pct']}"
        )
    lines += [
        "",
        "## Claim boundary",
        "",
        result["claim_boundary"],
        "",
        f"- Model comparison performed: **{validation['model_comparison_performed']}**",
        f"- Numeric validation gate closed: **{validation['numeric_validation_gate_closed']}**",
        f"- Full-loop external validation supported: **{validation['full_loop_external_validation_supported']}**",
        "",
        validation["next_step"],
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-directory", type=Path, default=Path("data/public_validation/raw/zenodo_4668554"))
    parser.add_argument("--json-output", type=Path, default=Path("research/grune_ventilation_dataset_inventory_2026_10_05.json"))
    parser.add_argument("--report-output", type=Path, default=Path("research/GRUNE_VENTILATION_DATASET_INVENTORY_2026_10_05.md"))
    args = parser.parse_args()
    result = build(args.raw_directory)
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.report_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.report_output.write_text(markdown(result), encoding="utf-8")
    print(json.dumps({"profiles": result["inventory"]["profile_count"], "points": result["inventory"]["spatial_point_count"], "identity_ok": result["inventory"]["source_identity_all_match"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
