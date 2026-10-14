"""Summarize the open Grüne/Sempert actual-H2 spatial workbooks.

This is a post-access development diagnostic.  It deliberately reports
measured spatial concentration fields as descriptive aggregates only: the
workbooks have no common time axis and were opened after the frozen spatial
holdout protocol, so this command never changes detector routing, thresholds,
runtime parameters, or a validation gate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np

from h2station.public_validation import GruneVentilationProfile, read_grune_ventilation_workbook


ROOT = Path(__file__).resolve().parents[1]
INTAKE = ROOT / "research/grune_ps_h2_dispersion_intake_2026_10_14.json"
THRESHOLDS_VOLPCT = (0.2, 0.4, 4.0)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _threshold_summary(profile: GruneVentilationProfile, threshold: float) -> dict[str, Any]:
    rows = [
        point for point in profile.points
        if point.concentration_average_pct is not None
    ]
    values = np.asarray([float(point.concentration_average_pct) for point in rows], dtype=float)
    above = [point for point in rows if float(point.concentration_average_pct) >= threshold]
    result: dict[str, Any] = {
        "threshold_volpct_h2": threshold,
        "measured_point_count": int(values.size),
        "point_count_at_or_above_threshold": len(above),
        "point_fraction_at_or_above_threshold": (
            float(len(above) / values.size) if values.size else None
        ),
        "coordinate_extent_is_descriptive": True,
    }
    if above:
        result.update({
            "x_min_mm": float(min(point.x_mm for point in above)),
            "x_max_mm": float(max(point.x_mm for point in above)),
            "y_min_mm": float(min(point.y_mm for point in above)),
            "y_max_mm": float(max(point.y_mm for point in above)),
        })
    else:
        result.update({"x_min_mm": None, "x_max_mm": None, "y_min_mm": None, "y_max_mm": None})
    return result


def _profile_summary(profile: GruneVentilationProfile) -> dict[str, Any]:
    values = np.asarray([
        float(point.concentration_average_pct)
        for point in profile.points
        if point.concentration_average_pct is not None
    ], dtype=float)
    summary = profile.summary()
    summary["thresholds"] = {
        str(threshold): _threshold_summary(profile, threshold)
        for threshold in THRESHOLDS_VOLPCT
    }
    summary["concentration_average_p50_pct"] = (
        float(np.percentile(values, 50)) if values.size else None
    )
    return summary


def analyze(raw_dir: Path, intake_path: Path = INTAKE) -> dict[str, Any]:
    intake = json.loads(intake_path.read_text(encoding="utf-8"))
    expected_files = {
        str(item["name"]): str(item["md5"])
        for item in (intake.get("integrity") or {}).get("files") or []
        if str(item.get("name", "")).lower().endswith((".xlsx", ".zip", ".pdf"))
    }
    integrity: list[dict[str, Any]] = []
    for name, expected_md5 in expected_files.items():
        path = raw_dir / name
        if not path.is_file():
            raise FileNotFoundError(f"missing intake file: {path}")
        md5 = hashlib.md5(path.read_bytes()).hexdigest()
        integrity.append({"name": name, "md5": md5, "md5_matches_intake": md5 == expected_md5})
    if not all(item["md5_matches_intake"] for item in integrity):
        raise ValueError("one or more source files do not match the committed intake manifest")

    profiles: list[GruneVentilationProfile] = []
    for path in sorted(raw_dir.glob("*.xlsx")):
        profiles.extend(read_grune_ventilation_workbook(path))
    hydrogen_profiles = [
        profile for profile in profiles
        if " h2" in f" {profile.sheet_name.lower()}" and " he" not in f" {profile.sheet_name.lower()}"
    ]
    helium_profiles = [profile for profile in profiles if profile not in hydrogen_profiles]
    if len(hydrogen_profiles) != 41:
        raise ValueError(f"expected 41 hydrogen sheets from intake, found {len(hydrogen_profiles)}")

    summaries = [_profile_summary(profile) for profile in hydrogen_profiles]
    all_values = np.asarray([
        float(point.concentration_average_pct)
        for profile in hydrogen_profiles
        for point in profile.points
        if point.concentration_average_pct is not None
    ], dtype=float)
    threshold_aggregate: dict[str, Any] = {}
    for threshold in THRESHOLDS_VOLPCT:
        rows = [item["thresholds"][str(threshold)] for item in summaries]
        threshold_aggregate[str(threshold)] = {
            "threshold_volpct_h2": threshold,
            "profile_count_with_any_point_at_or_above_threshold": sum(
                bool(item["point_count_at_or_above_threshold"]) for item in rows
            ),
            "median_point_fraction_at_or_above_threshold": float(
                np.median([item["point_fraction_at_or_above_threshold"] for item in rows])
            ),
            "coordinate_extent_is_descriptive": True,
        }

    return {
        "schema_version": 1,
        "artifact_type": "post_access_actual_hydrogen_spatial_diagnostic",
        "recorded_at": "2026-10-14",
        "status": "POST_ACCESS_DEVELOPMENT_DIAGNOSTIC",
        "source": {
            "title": "Efficiency of mechanical ventilation on H2 dispersion (PS)",
            "doi": "10.5281/zenodo.4668554",
            "record_url": "https://zenodo.org/records/4668554",
            "license": "CC BY 4.0",
        },
        "integrity": {
            "intake_artifact": str(intake_path.relative_to(ROOT)).replace("\\", "/"),
            "source_files": integrity,
            "all_md5_match": True,
        },
        "dataset": {
            "hydrogen_profile_count": len(hydrogen_profiles),
            "helium_profile_count_excluded": len(helium_profiles),
            "hydrogen_point_count": int(sum(len(profile.points) for profile in hydrogen_profiles)),
            "average_concentration_p50_pct": float(np.percentile(all_values, 50)),
            "average_concentration_p95_pct": float(np.percentile(all_values, 95)),
            "threshold_aggregates": threshold_aggregate,
        },
        "profiles": summaries,
        "eligibility_decision": {
            "independent_holdout": False,
            "runtime_parameter_updated": False,
            "validation_gate_changed": False,
            "promotion_prohibited": True,
            "reason": (
                "The workbooks were opened after the frozen spatial protocol and provide spatial snapshots, "
                "not a synchronized station or vehicle time-series holdout."
            ),
        },
        "claim_boundary": (
            "Measured actual-hydrogen concentration fields are summarized for development and manuscript context. "
            "Coordinate extents are not safety distances, evacuation radii, detector setpoints, CFD validation, "
            "or evidence of station-to-vehicle performance."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-dir", type=Path, default=ROOT / "data/public_validation/raw/zenodo_4668554")
    parser.add_argument("--output", type=Path, default=ROOT / "research/grune_ps_actual_h2_spatial_diagnostic_2026_10_14.json")
    args = parser.parse_args()
    result = analyze(args.raw_dir.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({
        "output": str(args.output),
        "status": result["status"],
        "hydrogen_profile_count": result["dataset"]["hydrogen_profile_count"],
        "hydrogen_point_count": result["dataset"]["hydrogen_point_count"],
        "runtime_parameter_updated": result["eligibility_decision"]["runtime_parameter_updated"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
