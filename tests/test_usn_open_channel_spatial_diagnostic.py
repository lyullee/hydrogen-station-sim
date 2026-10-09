from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_usn_coordinates_and_diagnostic_keep_claim_boundary_explicit() -> None:
    coordinates = json.loads(
        (ROOT / "research/usn_open_channel_sensor_coordinates_2026_10_10.json").read_text(
            encoding="utf-8"
        )
    )
    assert len(coordinates["sensors_m"]) == 29
    assert coordinates["coordinate_frame"]["release_orientation"] == "downward"

    diagnostic = json.loads(
        (ROOT / "research/usn_open_channel_spatial_diagnostic_2026_10_10.json").read_text(
            encoding="utf-8"
        )
    )
    aggregate = diagnostic["results"]["aggregate"]
    assert diagnostic["source"]["raw_archive_count"] == aggregate["experiment_count"] == 22
    assert aggregate["sensor_coordinate_count"] == 29
    assert diagnostic["method"]["runtime_parameter_application"] is False
    assert diagnostic["decision"]["spatial_holdout_ready"] is False
    assert diagnostic["decision"]["runtime_detector_routing_changed"] is False
    assert diagnostic["decision"]["claim_supported"] is False
