"""Build a privacy-safe empirical envelope from the public Grune workbooks.

The workbooks are downloaded outside Git and verified by the inventory manifest.
This script emits only derived means and ratios; it never copies workbook rows.
The ratio is defined against the same diameter/release-rate no-wind profile and
is intended as a bounded ventilation adjustment for the virtual detector proxy.
It is not a CFD calibration or a station-scale validation result.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import median

from h2station.public_validation import GruneVentilationProfile, read_grune_ventilation_workbook


def _profile_mean(profile: GruneVentilationProfile) -> float:
    values = [
        point.concentration_average_pct
        for point in profile.points
        if point.concentration_average_pct is not None
    ]
    if not values:
        raise ValueError(f"profile has no average concentration: {profile.sheet_name}")
    return float(median(values))


def build(input_dir: Path) -> dict:
    profiles: list[GruneVentilationProfile] = []
    for workbook in sorted(input_dir.glob("*.xlsx")):
        if "FLMT" in workbook.name:
            continue
        profiles.extend(read_grune_ventilation_workbook(workbook))
    if not profiles:
        raise FileNotFoundError(f"No Grune concentration workbooks under {input_dir}")

    baselines: dict[tuple[float, float], float] = {}
    for profile in profiles:
        if profile.wind_mode == "no-wind":
            key = (profile.release_diameter_mm, profile.nominal_release_g_s)
            baselines[key] = _profile_mean(profile)

    factors = []
    for profile in profiles:
        key = (profile.release_diameter_mm, profile.nominal_release_g_s)
        baseline = baselines.get(key)
        mean = _profile_mean(profile)
        if baseline is None or baseline <= 0.0:
            continue
        factors.append({
            "diameter_mm": profile.release_diameter_mm,
            "nominal_release_g_s": profile.nominal_release_g_s,
            "wind_mode": profile.wind_mode,
            "wind_speed_m_s": profile.wind_speed_m_s,
            "measured_mean_concentration_vol_pct": mean,
            "no_wind_reference_vol_pct": baseline,
            "relative_factor": mean / baseline,
            "point_count": len(profile.points),
        })

    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "derived_empirical_ventilation_envelope",
        "source": {
            "title": "Efficiency of mechanical ventilation on H2 dispersion (PS)",
            "doi": "10.5281/zenodo.4668554",
            "record": "https://zenodo.org/records/4668554",
            "license": "CC BY 4.0",
            "raw_rows_committed": False,
        },
        "definition": {
            "reference": "same release diameter and nominal release rate, no-wind profile",
            "quantity": "median of measured spatial-average concentration values",
            "use": "bounded multiplier for the virtual detector concentration proxy",
            "fallback": "1.0 when no matching public envelope is available",
            "not_a_claim": "not CFD, not detector certification, not outdoor HRS or full-loop validation",
        },
        "profiles_used": len(profiles),
        "factor_count": len(factors),
        "factors": factors,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = build(args.input_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"profiles_used": result["profiles_used"], "factor_count": result["factor_count"]}))


if __name__ == "__main__":
    main()
