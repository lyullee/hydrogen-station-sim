from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_usn_channel_spatial_stratification_evidence import (  # noqa: E402
    SENSOR_GEOMETRY,
)


def test_usn_spatial_geometry_is_complete_and_matches_published_strata() -> None:
    assert len(SENSOR_GEOMETRY) == 29
    assert sum(item["placement"] == "top" for item in SENSOR_GEOMETRY.values()) == 13
    assert sum(item["placement"] == "mid-high" for item in SENSOR_GEOMETRY.values()) == 5
    assert sum(item["placement"] == "mid-low" for item in SENSOR_GEOMETRY.values()) == 5
    assert sum(item["placement"] == "bottom" for item in SENSOR_GEOMETRY.values()) == 6
    assert {item["z_m"] for item in SENSOR_GEOMETRY.values()} == {
        0.0,
        0.27,
        0.28,
        0.52,
        0.8,
    }


def test_committed_usn_spatial_evidence_is_bounded_and_complete() -> None:
    result = json.loads(
        (
            ROOT
            / "research/usn_channel_spatial_stratification_evidence_2026_10_08.json"
        ).read_text(encoding="utf-8")
    )
    assert result["artifact_type"] == (
        "post_access_actual_hydrogen_spatial_stratification_evidence"
    )
    assert result["source"]["dataset_doi"] == "10.23642/usn.26117989.v2"
    assert result["source"]["article_doi"] == "10.1016/j.jlp.2025.105669"
    assert result["source"]["test_gas"] == "hydrogen"
    assert result["analysis_design"]["outcomes_accessed_before_analysis_design"] is True
    assert result["analysis_design"]["parameter_fitting_performed"] is False
    aggregate = result["aggregate"]
    assert aggregate["experiment_count"] == 22
    assert aggregate["sensor_count_per_experiment"] == 29
    assert aggregate["sensor_case_observation_count"] == 638
    assert aggregate["height_vs_steady_concentration_spearman_rho"][
        "positive_fraction"
    ] == 1.0
    assert aggregate["placements"]["top"]["alarm"]["coverage_fraction"] == 1.0
    assert aggregate["placements"]["top"]["trip"]["coverage_fraction"] == 1.0
    near_source = aggregate["jet_path_subsets"]["near_source_bottom"]
    assert near_source["sensor_ids"] == ["20", "21", "22"]
    assert near_source["sensor_case_observation_count"] == 66
    assert near_source["alarm"]["coverage_fraction"] == 1.0
    assert near_source["trip"]["coverage_fraction"] == 1.0
    assert near_source["alarm"]["median_latency_after_fill_start_s"] < 11.0
    assert aggregate["top_placement_highest_case_mean_count"] >= 20
    decision = result["decision"]
    assert decision["layered_confined_detector_placement_rationale_supported"] is True
    assert decision["independent_spatial_validation_supported"] is False
    assert decision["runtime_application"] is False
    assert decision["h2safe_gate_changed"] is False
    assert decision["full_loop_validation_supported"] is False
