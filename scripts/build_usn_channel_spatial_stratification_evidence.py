"""Build bounded spatial detector-placement evidence from physical H2 tests.

The source outcomes were already available before this analysis was designed.
The result is therefore descriptive, post-access evidence.  It may support a
layered detector-placement rationale, but it cannot validate the station map,
change runtime routing, or close the independent H2SAFE transfer gate.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
from statistics import mean, median
from typing import Any

import numpy as np
from scipy.stats import spearmanr

from h2station.public_validation import (
    first_persistent_threshold_time,
    iter_dispersion_experiments,
)


# Coordinates transcribed from Table 1 of Henriksen et al. (2025).  The source
# defines x across the channel, y from the closed end, and z above the floor.
SENSOR_GEOMETRY: dict[str, dict[str, Any]] = {
    "1": {"placement": "top", "x_m": 0.77, "y_m": 0.24, "z_m": 0.80},
    "2": {"placement": "top", "x_m": 0.46, "y_m": 0.00, "z_m": 0.80},
    "3": {"placement": "mid-high", "x_m": 0.48, "y_m": 0.25, "z_m": 0.52},
    "4": {"placement": "top", "x_m": 0.13, "y_m": 0.26, "z_m": 0.80},
    "5": {"placement": "mid-high", "x_m": 0.48, "y_m": 1.33, "z_m": 0.52},
    "6": {"placement": "top", "x_m": 0.46, "y_m": 1.11, "z_m": 0.80},
    "7": {"placement": "top", "x_m": 0.90, "y_m": 2.22, "z_m": 0.80},
    "8": {"placement": "mid-high", "x_m": 0.47, "y_m": 2.46, "z_m": 0.52},
    "9": {"placement": "top", "x_m": 0.46, "y_m": 2.22, "z_m": 0.80},
    "10": {"placement": "top", "x_m": 0.74, "y_m": 2.45, "z_m": 0.80},
    "11": {"placement": "top", "x_m": 0.15, "y_m": 2.44, "z_m": 0.80},
    "12": {"placement": "top", "x_m": 0.00, "y_m": 2.22, "z_m": 0.80},
    "13": {"placement": "mid-high", "x_m": 0.47, "y_m": 3.54, "z_m": 0.52},
    "14": {"placement": "top", "x_m": 0.46, "y_m": 3.31, "z_m": 0.80},
    "15": {"placement": "top", "x_m": 0.78, "y_m": 4.65, "z_m": 0.80},
    "17": {"placement": "top", "x_m": 0.46, "y_m": 4.39, "z_m": 0.80},
    "18": {"placement": "mid-high", "x_m": 0.47, "y_m": 4.63, "z_m": 0.52},
    "19": {"placement": "top", "x_m": 0.14, "y_m": 4.68, "z_m": 0.80},
    "20": {"placement": "bottom", "x_m": 0.75, "y_m": 0.24, "z_m": 0.00},
    "21": {"placement": "bottom", "x_m": 0.45, "y_m": 0.00, "z_m": 0.00},
    "22": {"placement": "bottom", "x_m": 0.16, "y_m": 0.24, "z_m": 0.00},
    "23": {"placement": "mid-low", "x_m": 0.47, "y_m": 0.24, "z_m": 0.28},
    "24": {"placement": "mid-low", "x_m": 0.46, "y_m": 1.33, "z_m": 0.27},
    "25": {"placement": "bottom", "x_m": 0.47, "y_m": 1.10, "z_m": 0.00},
    "26": {"placement": "mid-low", "x_m": 0.46, "y_m": 2.46, "z_m": 0.27},
    "27": {"placement": "bottom", "x_m": 0.47, "y_m": 2.23, "z_m": 0.00},
    "28": {"placement": "mid-low", "x_m": 0.47, "y_m": 3.56, "z_m": 0.27},
    "29": {"placement": "mid-low", "x_m": 0.47, "y_m": 4.63, "z_m": 0.27},
    "30": {"placement": "bottom", "x_m": 0.46, "y_m": 4.44, "z_m": 0.00},
}
NEAR_SOURCE_BOTTOM_SENSOR_IDS = frozenset({"20", "21", "22"})


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _median_or_none(values: list[float]) -> float | None:
    return float(median(values)) if values else None


def _mean_or_none(values: list[float]) -> float | None:
    return float(mean(values)) if values else None


def _steady_sensor_means(experiment: Any) -> np.ndarray:
    start = experiment.baseline_duration_s + 2.0 * experiment.filling_duration_s / 3.0
    end = experiment.baseline_duration_s + experiment.filling_duration_s
    mask = (experiment.sensor_time_s >= start) & (experiment.sensor_time_s <= end)
    if not np.any(mask):
        raise ValueError(f"{experiment.case_id} has no steady-interval samples")
    return np.mean(np.maximum(experiment.concentrations_percent[mask], 0.0), axis=0)


def build(
    raw_directory: Path,
    *,
    alarm_threshold_percent: float = 1.0,
    trip_threshold_percent: float = 2.0,
    persistence_s: float = 0.5,
) -> dict[str, Any]:
    if alarm_threshold_percent >= trip_threshold_percent:
        raise ValueError("alarm threshold must be below trip threshold")
    experiments = list(iter_dispersion_experiments(raw_directory))
    if not experiments:
        raise ValueError("No dispersion experiments were found")

    grouped: dict[str, dict[str, list[float]]] = defaultdict(
        lambda: defaultdict(list)
    )
    cases: list[dict[str, Any]] = []
    correlations: list[float] = []
    top_quartile_shares: list[float] = []
    top_group_highest_count = 0

    for experiment in experiments:
        missing = sorted(set(experiment.sensor_ids) - set(SENSOR_GEOMETRY))
        if missing:
            raise ValueError(f"Unmapped sensors in {experiment.case_id}: {missing}")
        if len(experiment.sensor_ids) != len(SENSOR_GEOMETRY):
            raise ValueError(
                f"{experiment.case_id} has {len(experiment.sensor_ids)} sensors; expected 29"
            )

        steady = _steady_sensor_means(experiment)
        heights = np.asarray(
            [SENSOR_GEOMETRY[sensor_id]["z_m"] for sensor_id in experiment.sensor_ids],
            dtype=float,
        )
        rho = float(spearmanr(heights, steady).statistic)
        if not math.isfinite(rho):
            raise ValueError(f"Non-finite height response correlation in {experiment.case_id}")
        correlations.append(rho)

        highest_quartile_count = math.ceil(len(steady) * 0.25)
        highest_indices = np.argsort(steady)[-highest_quartile_count:]
        highest_top_count = sum(
            SENSOR_GEOMETRY[experiment.sensor_ids[int(index)]]["placement"] == "top"
            for index in highest_indices
        )
        top_share = highest_top_count / highest_quartile_count
        top_quartile_shares.append(top_share)

        group_case_means: dict[str, float] = {}
        for placement in ("top", "mid-high", "mid-low", "bottom"):
            indices = [
                index
                for index, sensor_id in enumerate(experiment.sensor_ids)
                if SENSOR_GEOMETRY[sensor_id]["placement"] == placement
            ]
            group_case_means[placement] = float(np.mean(steady[indices]))
        if max(group_case_means, key=group_case_means.get) == "top":
            top_group_highest_count += 1

        for index, sensor_id in enumerate(experiment.sensor_ids):
            placement = SENSOR_GEOMETRY[sensor_id]["placement"]
            values = experiment.concentrations_percent[:, index]
            alarm_time = first_persistent_threshold_time(
                experiment.sensor_time_s,
                values,
                alarm_threshold_percent,
                persistence_s,
            )
            trip_time = first_persistent_threshold_time(
                experiment.sensor_time_s,
                values,
                trip_threshold_percent,
                persistence_s,
            )
            grouped[placement]["steady_concentration_percent"].append(float(steady[index]))
            grouped[placement]["alarm_detected"].append(float(alarm_time is not None))
            grouped[placement]["trip_detected"].append(float(trip_time is not None))
            if sensor_id in NEAR_SOURCE_BOTTOM_SENSOR_IDS:
                grouped["near-source-bottom"]["steady_concentration_percent"].append(
                    float(steady[index])
                )
                grouped["near-source-bottom"]["alarm_detected"].append(
                    float(alarm_time is not None)
                )
                grouped["near-source-bottom"]["trip_detected"].append(
                    float(trip_time is not None)
                )
            if alarm_time is not None:
                grouped[placement]["alarm_latency_after_fill_start_s"].append(
                    float(alarm_time - experiment.baseline_duration_s)
                )
                if sensor_id in NEAR_SOURCE_BOTTOM_SENSOR_IDS:
                    grouped["near-source-bottom"][
                        "alarm_latency_after_fill_start_s"
                    ].append(float(alarm_time - experiment.baseline_duration_s))
            if trip_time is not None:
                grouped[placement]["trip_latency_after_fill_start_s"].append(
                    float(trip_time - experiment.baseline_duration_s)
                )
                if sensor_id in NEAR_SOURCE_BOTTOM_SENSOR_IDS:
                    grouped["near-source-bottom"][
                        "trip_latency_after_fill_start_s"
                    ].append(float(trip_time - experiment.baseline_duration_s))

        cases.append(
            {
                "case_id": experiment.case_id,
                "article_test_id": experiment.article_test_id,
                "mean_mass_flow_g_s": experiment.mean_mass_flow_g_s,
                "height_vs_steady_concentration_spearman_rho": rho,
                "top_share_of_highest_response_quartile": top_share,
                "highest_mean_placement": max(group_case_means, key=group_case_means.get),
                "placement_steady_mean_percent": group_case_means,
            }
        )

    def summarize_group(values: dict[str, list[float]]) -> dict[str, Any]:
        steady_values = values["steady_concentration_percent"]
        alarm_flags = values["alarm_detected"]
        trip_flags = values["trip_detected"]
        return {
            "sensor_case_observation_count": len(steady_values),
            "steady_concentration_percent": {
                "median": float(median(steady_values)),
                "mean": float(mean(steady_values)),
            },
            "alarm": {
                "coverage_fraction": float(mean(alarm_flags)),
                "detected_count": int(sum(alarm_flags)),
                "median_latency_after_fill_start_s": _median_or_none(
                    values["alarm_latency_after_fill_start_s"]
                ),
            },
            "trip": {
                "coverage_fraction": float(mean(trip_flags)),
                "detected_count": int(sum(trip_flags)),
                "median_latency_after_fill_start_s": _median_or_none(
                    values["trip_latency_after_fill_start_s"]
                ),
            },
        }

    placement_results: dict[str, Any] = {
        placement: summarize_group(grouped[placement])
        for placement in ("top", "mid-high", "mid-low", "bottom")
    }
    near_source_bottom = summarize_group(grouped["near-source-bottom"])
    near_source_bottom.update(
        {
            "sensor_ids": sorted(NEAR_SOURCE_BOTTOM_SENSOR_IDS, key=int),
            "selection": "three floor probes nearest the downward jet origin",
        }
    )

    support_files = []
    for name in ("article_105669.pdf", "article_105669.txt", "ReadMe.txt"):
        path = raw_directory / name
        if path.is_file():
            support_files.append(
                {"name": name, "bytes": path.stat().st_size, "sha256": _sha256(path)}
            )

    return {
        "schema_version": 1,
        "artifact_type": "post_access_actual_hydrogen_spatial_stratification_evidence",
        "status": "COMPLETED_DESCRIPTIVE_EVIDENCE_NOT_INDEPENDENT_VALIDATION",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": {
            "dataset_title": "Experimental Data of Hydrogen Dispersion in an Open-ended Rectangular Channel",
            "dataset_doi": "10.23642/usn.26117989.v2",
            "article_title": "A study of hydrogen dispersion in an open-ended rectangular channel",
            "article_doi": "10.1016/j.jlp.2025.105669",
            "test_gas": "hydrogen",
            "license": "CC BY 4.0",
            "channel_dimensions_m": {"length_y": 5.8, "width_x": 0.9, "height_z": 0.8},
            "release": {
                "x_m": 0.45,
                "y_m": 0.5,
                "z_m": 0.8,
                "orientation": "downward",
                "diameter_mm": 4.6,
            },
            "coordinate_source": "Henriksen et al. (2025), Table 1",
            "supporting_file_manifest": support_files,
            "archive_count": len(list(raw_directory.glob("*.zip"))),
            "archive_manifest_sha256": hashlib.sha256(
                "\n".join(
                    f"{path.name}:{_sha256(path)}"
                    for path in sorted(raw_directory.glob("*.zip"))
                ).encode("utf-8")
            ).hexdigest(),
        },
        "analysis_design": {
            "outcomes_accessed_before_analysis_design": True,
            "post_access_descriptive_evidence": True,
            "parameter_fitting_performed": False,
            "steady_interval": "final third of each declared fill interval",
            "alarm_threshold_percent": alarm_threshold_percent,
            "trip_threshold_percent": trip_threshold_percent,
            "persistence_s": persistence_s,
            "highest_response_quartile_count_per_case": 8,
        },
        "geometry": {
            "sensor_count": len(SENSOR_GEOMETRY),
            "placement_sensor_counts": {
                placement: sum(
                    geometry["placement"] == placement
                    for geometry in SENSOR_GEOMETRY.values()
                )
                for placement in ("top", "mid-high", "mid-low", "bottom")
            },
            "sensors": SENSOR_GEOMETRY,
        },
        "aggregate": {
            "experiment_count": len(experiments),
            "sensor_count_per_experiment": 29,
            "sensor_case_observation_count": len(experiments) * len(SENSOR_GEOMETRY),
            "height_vs_steady_concentration_spearman_rho": {
                "median": float(median(correlations)),
                "mean": float(mean(correlations)),
                "positive_fraction": float(mean(value > 0 for value in correlations)),
            },
            "top_share_of_highest_response_quartile": {
                "median": float(median(top_quartile_shares)),
                "mean": float(mean(top_quartile_shares)),
            },
            "top_placement_highest_case_mean_count": top_group_highest_count,
            "top_placement_highest_case_mean_fraction": top_group_highest_count / len(experiments),
            "placements": placement_results,
            "jet_path_subsets": {
                "near_source_bottom": near_source_bottom,
            },
        },
        "cases": cases,
        "decision": {
            "bounded_actual_hydrogen_spatial_stratification_supported": True,
            "layered_confined_detector_placement_rationale_supported": True,
            "ceiling_layer_coverage_supported": True,
            "near_source_jet_path_supplement_supported": True,
            "independent_spatial_validation_supported": False,
            "runtime_application": False,
            "runtime_parameter_changed": False,
            "h2safe_gate_changed": False,
            "outdoor_station_detector_map_validated": False,
            "full_loop_validation_supported": False,
        },
        "claim_boundary": (
            "Twenty-two physical-hydrogen tests support a descriptive layered-placement "
            "rationale inside this open-ended 5.8 m channel: ceiling probes provide broad "
            "sustained coverage, while probes in the downward-jet path can respond earlier. "
            "Because outcomes were accessed before this analysis was designed, this is not "
            "independent validation and cannot validate an outdoor station detector map, "
            "alarm setpoints, ESD effectiveness, runtime spatial routing, or the full digital twin."
        ),
    }


def markdown(result: dict[str, Any]) -> str:
    aggregate = result["aggregate"]
    top = aggregate["placements"]["top"]
    near_source = aggregate["jet_path_subsets"]["near_source_bottom"]
    lines = [
        "# USN/FFI actual-hydrogen spatial stratification evidence",
        "",
        f"Generated: `{result['generated_at']}`",
        "",
        "## Decision",
        "",
        "This is post-access descriptive evidence, not an independent detector-map validation.",
        "",
        f"- Experiments: **{aggregate['experiment_count']}**",
        f"- Sensors per experiment: **{aggregate['sensor_count_per_experiment']}**",
        f"- Sensor-case observations: **{aggregate['sensor_case_observation_count']}**",
        f"- Top sensors: alarm/trip coverage **{top['alarm']['coverage_fraction']:.1%} / {top['trip']['coverage_fraction']:.1%}**",
        f"- Near-source bottom sensors: median alarm latency **{near_source['alarm']['median_latency_after_fill_start_s']:.2f} s** under the downward jet",
        f"- Top placement had the highest case mean in **{aggregate['top_placement_highest_case_mean_count']}/{aggregate['experiment_count']}** tests",
        "",
        "## Engineering interpretation",
        "",
        "The physical-H2 records support layered coverage in this confined geometry: ceiling detection for the sustained buoyant layer, supplemented by near-source coverage along the downward jet path. Exact station locations and outdoor transfer remain unvalidated.",
        "",
        "## Placement results",
        "",
        "| Placement | Observations | Median steady H2 | Alarm coverage | Median alarm latency | Trip coverage |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for placement in ("top", "mid-high", "mid-low", "bottom"):
        item = aggregate["placements"][placement]
        alarm_latency = item["alarm"]["median_latency_after_fill_start_s"]
        lines.append(
            f"| {placement} | {item['sensor_case_observation_count']} | "
            f"{item['steady_concentration_percent']['median']:.3f} vol% | "
            f"{item['alarm']['coverage_fraction']:.1%} | "
            f"{alarm_latency:.2f} s | {item['trip']['coverage_fraction']:.1%} |"
        )
    lines.extend(
        [
            "",
            "## Claim boundary",
            "",
            result["claim_boundary"],
            "",
            "## Sources",
            "",
            "- Dataset: https://doi.org/10.23642/usn.26117989.v2",
            "- Article: https://doi.org/10.1016/j.jlp.2025.105669",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--raw",
        type=Path,
        default=Path("data/public_validation/raw/hydrogen_dispersion_channel"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("research/usn_channel_spatial_stratification_evidence_2026_10_08.json"),
    )
    parser.add_argument(
        "--markdown",
        type=Path,
        default=Path("research/USN_CHANNEL_SPATIAL_STRATIFICATION_EVIDENCE_2026_10_08.md"),
    )
    args = parser.parse_args()
    result = build(args.raw)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    args.markdown.write_text(markdown(result), encoding="utf-8")
    print(
        f"completed {result['aggregate']['experiment_count']} experiments; "
        f"{result['aggregate']['sensor_case_observation_count']} sensor-case observations",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
