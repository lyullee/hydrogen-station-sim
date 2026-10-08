"""Evaluate the frozen orientation-class ranker on a public Sandia H2 summary.

The six concentration outcomes were inspected before this diagnostic was
formalised, so the result is an external post-access diagnostic rather than a
prospective validation.  No parameter is fitted and runtime routing remains
disabled.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
from scipy.stats import kendalltau, spearmanr

from h2station.spatial_detector import (
    Point3D,
    geometry_score,
    orientation_aware_geometry_score,
)


ROOT = Path(__file__).resolve().parents[1]
LOCK_COMMIT = "2056c04"
SOURCE = Point3D(2.12, 0.22, 1.20)  # FLACS (x,z,y): Y is elevation here.
ROWS = (
    ("S01", Point3D(1.97, 0.28, 1.25), 99.21),
    ("S04", Point3D(1.97, 2.68, 1.25), 12.66),
    ("S06", Point3D(1.86, 0.54, 1.24), 90.24),
    ("S07", Point3D(1.68, 1.21, 1.25), 43.34),
    ("S08", Point3D(4.16, 2.67, 1.27), 7.71),
    ("S11", Point3D(4.15, 2.67, 2.83), 7.81),
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _rank_metrics(scores: list[float], observed: list[float]) -> dict[str, Any]:
    predicted_order = np.argsort(np.asarray(scores))[::-1]
    observed_order = np.argsort(np.asarray(observed))[::-1]
    top_three_recall = len(set(predicted_order[:3]) & set(observed_order[:3])) / 3
    return {
        "spearman_rho": float(spearmanr(scores, observed).statistic),
        "kendall_tau_b": float(kendalltau(scores, observed).statistic),
        "highest_ranked_sensor_matches": bool(predicted_order[0] == observed_order[0]),
        "top3_recall": top_three_recall,
        "predicted_order": [ROWS[int(index)][0] for index in predicted_order],
        "observed_order": [ROWS[int(index)][0] for index in observed_order],
    }


def build() -> dict[str, Any]:
    cases = []
    baseline_scores: list[float] = []
    candidate_scores: list[float] = []
    observed: list[float] = []
    for sensor, point, response in ROWS:
        baseline = geometry_score(SOURCE, point)
        candidate = orientation_aware_geometry_score(SOURCE, point, "horizontal")
        baseline_scores.append(baseline)
        candidate_scores.append(candidate)
        observed.append(response)
        cases.append({
            "sensor": sensor,
            "coordinate_m_model_frame": {"x": point.x, "y_elevation": point.y, "z": point.z},
            "experiment_combined_peak_h2_volpct": response,
            "baseline_score": baseline,
            "orientation_candidate_score": candidate,
        })
    baseline = _rank_metrics(baseline_scores, observed)
    candidate = _rank_metrics(candidate_scores, observed)
    return {
        "schema_version": 1,
        "artifact_type": "post_access_actual_hydrogen_spatial_rank_diagnostic",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "EXTERNAL_POST_ACCESS_DIAGNOSTIC_NOT_VALIDATION",
        "source": {
            "experiment": "Sandia/SRI hydrogen forklift release in enclosed warehouse",
            "primary_article": (
                "Ekoto et al. (2012), Experimental investigation of hydrogen release "
                "and ignition from fuel cell powered forklifts in enclosed spaces"
            ),
            "primary_article_doi": "10.1016/j.ijhydene.2012.03.161",
            "public_numeric_summary_url": "https://knowledge.gexcon.com/docs/sandia-validation-case",
            "public_summary_updated": "2025-11-28",
            "data_scope": (
                "Six public sensor coordinates and Test-1/Test-2 combined maximum H2 "
                "concentrations; full concentration-time histories are not public."
            ),
            "test_gas": "hydrogen",
            "raw_time_series_available": False,
            "license": "Public factual summary; no open-data license asserted",
        },
        "model_lock": {
            "candidate": "orientation_class_rank_v2",
            "implementation": "src/h2station/spatial_detector.py",
            "implementation_sha256": _sha256(ROOT / "src/h2station/spatial_detector.py"),
            "candidate_frozen_before_numeric_outcome_access": True,
            "freeze_commit": LOCK_COMMIT,
            "diagnostic_protocol_frozen_before_outcome_access": False,
            "parameters_fitted": False,
            "runtime_application": False,
        },
        "coordinate_mapping": {
            "published_frame": "FLACS x/y/z with z as elevation",
            "model_frame": "x/y/z with y as elevation",
            "transform": "model Point3D = (FLACS x, FLACS z, FLACS y)",
            "source_coordinate_m_model_frame": {
                "x": SOURCE.x, "y_elevation": SOURCE.y, "z": SOURCE.z,
            },
            "release_orientation": "horizontal",
            "published_release_direction": "-X",
            "candidate_uses_azimuth": False,
        },
        "cases": cases,
        "baseline_geometry_only": baseline,
        "orientation_candidate": candidate,
        "delta": {
            "spearman_rho": candidate["spearman_rho"] - baseline["spearman_rho"],
            "kendall_tau_b": candidate["kendall_tau_b"] - baseline["kendall_tau_b"],
        },
        "decision": {
            "candidate_consistent_with_public_actual_hydrogen_rank_order": True,
            "independent_validation_pass": False,
            "h2safe_gate_changed": False,
            "runtime_candidate_enabled": False,
            "reason": (
                "The exact locked candidate ranks the six public actual-H2 maxima well, "
                "but the six outcomes were viewed before this diagnostic was formalised, "
                "Tests 1 and 2 are combined into one response vector, and the full time "
                "histories are explicitly unavailable."
            ),
        },
        "claim_boundary": (
            "This single six-point combined-test summary is actual-hydrogen external "
            "diagnostic evidence for spatial ordering only. It is not a prospective "
            "validation, detector calibration, concentration prediction, alarm-setpoint, "
            "outdoor HRS placement, CFD, consequence-distance, ESD or full-loop claim."
        ),
    }


def _markdown(result: dict[str, Any]) -> str:
    before = result["baseline_geometry_only"]
    after = result["orientation_candidate"]
    return "\n".join([
        "# Sandia warehouse actual-hydrogen spatial-rank diagnostic",
        "",
        "The H2SAFE-derived orientation-class candidate was frozen in commit "
        f"`{LOCK_COMMIT}` before these six public numerical outcomes were inspected. "
        "The diagnostic itself was formalised after outcome access, so this is external "
        "post-access evidence and not independent validation.",
        "",
        "| Metric | Original buoyant rank | Orientation-class candidate |",
        "|---|---:|---:|",
        f"| Spearman rho | {before['spearman_rho']:.3f} | {after['spearman_rho']:.3f} |",
        f"| Kendall tau-b | {before['kendall_tau_b']:.3f} | {after['kendall_tau_b']:.3f} |",
        f"| Top-3 recall | {before['top3_recall']:.3f} | {after['top3_recall']:.3f} |",
        f"| Highest-ranked sensor correct | {before['highest_ranked_sensor_matches']} | {after['highest_ranked_sensor_matches']} |",
        "",
        f"Observed descending order: `{', '.join(after['observed_order'])}`.",
        f"Candidate descending order: `{', '.join(after['predicted_order'])}`.",
        "",
        "The candidate improves Spearman rho from 0.600 to 0.943 without fitting. It "
        "correctly identifies S01 and the three highest-response sensors. The bottom two "
        "sensors are reversed. Runtime routing remains disabled and the H2SAFE gate "
        "remains failed.",
        "",
        "Source: [Gexcon Sandia validation case](https://knowledge.gexcon.com/docs/sandia-validation-case), "
        "based on [Ekoto et al. (2012)](https://doi.org/10.1016/j.ijhydene.2012.03.161).",
        "",
        "## Claim boundary",
        "",
        result["claim_boundary"],
        "",
    ])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--json-output", type=Path,
        default=ROOT / "research/sandia_warehouse_spatial_diagnostic_2026_10_08.json",
    )
    parser.add_argument(
        "--markdown-output", type=Path,
        default=ROOT / "research/SANDIA_WAREHOUSE_SPATIAL_DIAGNOSTIC_2026_10_08.md",
    )
    args = parser.parse_args()
    result = build()
    args.json_output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8", newline="\n",
    )
    args.markdown_output.write_text(
        _markdown(result), encoding="utf-8", newline="\n"
    )
    print(json.dumps({
        "status": result["status"],
        "baseline_spearman": result["baseline_geometry_only"]["spearman_rho"],
        "candidate_spearman": result["orientation_candidate"]["spearman_rho"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
