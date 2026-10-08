import json
from pathlib import Path
import re

import pytest

from h2station.spatial_detector import (
    DETECTOR_POSITIONS,
    Point3D,
    detector_weights,
    geometry_score,
    orientation_aware_geometry_score,
    ranked_detector_tags,
    spatial_proxy_metadata,
)


ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT / "research/h2safe_spatial_response_diagnostic_2026_10_08.json"
ORIENTATION_RESULT = ROOT / "research/h2safe_orientation_development_2026_10_08.json"


def test_geometry_ranking_uses_station_y_axis_as_elevation():
    source = Point3D(0.0, 0.0, 0.0)
    elevated = Point3D(1.0, 2.0, 0.0)
    equally_distant_below = Point3D(1.0, -2.0, 0.0)
    assert geometry_score(source, elevated) > geometry_score(source, equally_distant_below)


def test_horizontal_orientation_candidate_prefers_release_height_without_azimuth():
    source = Point3D(0.0, 1.5, 0.0)
    same_height = Point3D(2.0, 1.5, 0.0)
    high = Point3D(2.0, 5.5, 0.0)
    assert orientation_aware_geometry_score(
        source, same_height, "horizontal"
    ) > orientation_aware_geometry_score(source, high, "horizontal")
    assert orientation_aware_geometry_score(
        source, high, "vertical"
    ) == geometry_score(source, high)


@pytest.mark.parametrize(
    ("target", "expected_near"),
    (
        ("cascade.low", "GD-0701"),
        ("cascade.medium", "GD-0801"),
        ("cascade.high", "GD-0901"),
        ("dispenser.hose", "GD-1301"),
        ("dispenser_2.hose", "GD-1701"),
        ("vent", "GD-2001"),
    ),
)
def test_station_release_ranks_the_local_head_first(target, expected_near):
    assert ranked_detector_tags(target)[0] == expected_near
    weights = detector_weights(target)
    assert weights[expected_near] == 1.0
    assert sorted(weights.values()) == [0.45, 1.0]


def test_h2safe_result_keeps_failed_joint_screen_and_claim_boundary_visible():
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    primary = result["results"]["Y_as_elevation"]["aggregate"]
    sensitivity = result["results"]["Z_as_elevation_sensitivity"]["aggregate"]
    assert result["method"]["status"] == "POST_ACCESS_DEVELOPMENT_DIAGNOSTIC_NOT_VALIDATION"
    assert primary["experiment_count"] == 5
    assert primary["joint_pass"] is False
    assert primary["median_spearman"] > sensitivity["median_spearman"]
    assert result["decision"]["joint_spatial_screen_pass"] is False
    assert "not independent validation" in result["claim_boundary"]


def test_runtime_metadata_does_not_claim_validated_dispersion():
    metadata = spatial_proxy_metadata()
    assert metadata["status"] == "EVALUATED_NOT_APPLIED_FAILED_JOINT_SCREEN"
    assert metadata["source_doi"] == "10.7799/17118570"
    assert metadata["runtime_application"] is False
    assert metadata["orientation_development_candidate"]["runtime_application"] is False
    assert "not CFD" in metadata["claim_limit"]


def test_orientation_candidate_passes_only_internal_development_screens():
    result = json.loads(ORIENTATION_RESULT.read_text(encoding="utf-8"))
    baseline = result["baseline"]["aggregate"]
    candidate = result["orientation_candidate"]["aggregate"]
    assert result["integrity"]["outcomes_seen_before_candidate_selection"] is True
    assert baseline["internal_reference_screen_pass"] is False
    assert candidate["internal_reference_screen_pass"] is True
    assert candidate["mean_top5_recall"] > baseline["mean_top5_recall"]
    assert candidate["nearest_in_response_quartile_fraction"] > baseline[
        "nearest_in_response_quartile_fraction"
    ]
    assert result["decision"]["independent_validation_pass"] is False
    assert result["decision"]["runtime_use"].startswith("PROHIBITED")


def test_backend_detector_coordinates_match_the_3d_scene_markers():
    source = (ROOT / "web/station3d.js").read_text(encoding="utf-8")
    marker_block = source.split("const detectorMarkerDefs=[", 1)[1].split(
        "].map(([id,label,x,y,z,name])", 1
    )[0]
    rows = re.findall(
        r"\['detector\d+','(GD-\d+)',(-?\d+(?:\.\d+)?),"
        r"(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?),'[^']+'\]",
        marker_block,
    )
    scene_positions = {
        tag: tuple(float(value) for value in (x, y, z))
        for tag, x, y, z in rows
    }
    assert set(scene_positions) == set(DETECTOR_POSITIONS)
    assert scene_positions == {
        tag: (point.x, point.y, point.z)
        for tag, point in DETECTOR_POSITIONS.items()
    }
