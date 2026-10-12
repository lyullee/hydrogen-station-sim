import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "research/h2safe_geometry_sensor_containment_2026_10_12.json"


def test_h2safe_public_mesh_contains_all_published_sensor_and_release_points():
    result = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    summary = result["summary"]
    assert summary["sensor_containment_fraction"] == 1.0
    assert summary["all_sensor_points_inside_mesh_bounds"] is True
    assert summary["all_release_points_inside_mesh_bounds"] is True


def test_h2safe_geometry_diagnostic_stays_fail_closed_for_runtime_and_registration():
    result = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    decision = result["decision"]
    assert result["summary"]["status"] == "CONTAINMENT_CONFIRMED_REGISTRATION_UNPROVEN"
    assert decision["runtime_application"] is False
    assert decision["preaccess_spatial_validation_ready"] is False
    assert "registration" in decision["interpretation"]
