"""Build the bounded virtual-detector coefficient from public concentration data.

This script deliberately produces a proxy policy, not a station-validation
score.  Each case contributes the 90th percentile concentration across the
measured sensor grid during the final third of its filling interval, normalized
by that case's measured mean release flow.  The runtime uses the median across
all 22 cases so one low-flow or high-flow experiment cannot dominate it.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import numpy as np

from h2station.public_validation import iter_dispersion_experiments


DOI = "10.23642/usn.26117989.v2"
LICENSE = "CC BY 4.0"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build(raw_directory: Path) -> dict:
    cases = []
    for experiment in iter_dispersion_experiments(raw_directory):
        start = experiment.baseline_duration_s + (2.0 * experiment.filling_duration_s / 3.0)
        end = experiment.baseline_duration_s + experiment.filling_duration_s
        steady = experiment.concentrations_percent[
            (experiment.sensor_time_s >= start) & (experiment.sensor_time_s <= end)
        ]
        if steady.size == 0 or experiment.mean_mass_flow_g_s <= 0.0:
            raise ValueError(f"{experiment.case_id} has no usable steady concentration data")
        steady = np.maximum(steady, 0.0)
        p90 = float(np.percentile(steady, 90.0))
        cases.append({
            "case_id": experiment.case_id,
            "article_test_id": experiment.article_test_id,
            "source_archive": experiment.source_archive,
            "mean_mass_flow_g_s": float(experiment.mean_mass_flow_g_s),
            "steady_interval_start_s": float(start),
            "steady_interval_end_s": float(end),
            "sensor_count": len(experiment.sensor_ids),
            "steady_concentration_p90_volpct_h2": p90,
            "p90_per_flow_volpct_per_g_s": p90 / float(experiment.mean_mass_flow_g_s),
        })
    if len(cases) < 20:
        raise ValueError("at least 20 public cases are required")
    ratios = np.asarray([item["p90_per_flow_volpct_per_g_s"] for item in cases], dtype=float)
    archives = []
    for path in sorted(raw_directory.glob("*.zip")):
        archives.append({"name": path.name, "bytes": path.stat().st_size, "sha256": _sha256(path)})
    return {
        "schema_version": 1,
        "status": "derived_bounded_dispersion_concentration_proxy",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": {
            "dataset": "Experimental Data of Hydrogen Dispersion in an Open-ended Rectangular Channel",
            "doi": DOI,
            "license": LICENSE,
            "raw_directory": str(raw_directory),
            "case_count": len(cases),
            "archive_manifest": archives,
        },
        "method": {
            "statistic": "median of per-case steady-final-third sensor-grid P90 concentration divided by measured mean release flow",
            "case_count": len(cases),
            "coefficient_volpct_per_g_s": float(np.median(ratios)),
            "coefficient_p25_volpct_per_g_s": float(np.percentile(ratios, 25.0)),
            "coefficient_p75_volpct_per_g_s": float(np.percentile(ratios, 75.0)),
            "min_volpct_per_g_s": float(np.min(ratios)),
            "max_volpct_per_g_s": float(np.max(ratios)),
        },
        "runtime_application": {
            "formula": "clip(release_mass_flow_g_s * coefficient_volpct_per_g_s * ventilation_multiplier, 0, 100)",
            "ventilation_multiplier_source": "research/grune_ventilation_empirical_envelope_2026_10_06.json",
            "fallback_when_artifact_missing": "use the recorded median coefficient and mark PUBLIC_DISPERSION_PROXY_FALLBACK",
        },
        "cases": cases,
        "claim_boundary": (
            "This coefficient is a bounded advisory virtual-detector proxy derived from an open-ended channel concentration dataset. "
            "It does not validate outdoor station dispersion, detector placement, detector response dynamics, ESD effectiveness, "
            "consequence distances, or the complete hydrogen-refuelling process model. A site-specific CFD or detector calibration "
            "study remains required for engineering or regulatory decisions."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", type=Path, default=Path("data/public_validation/raw/hydrogen_dispersion_channel"))
    parser.add_argument("--output", type=Path, default=Path("research/dispersion_concentration_proxy_calibration_2026_10_06.json"))
    args = parser.parse_args()
    result = build(args.raw)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.output} from {result['source']['case_count']} public cases")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
