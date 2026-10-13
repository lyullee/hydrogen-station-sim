from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_jetfire_archive_is_recorded_as_post_access_only() -> None:
    artifact = json.loads(
        (ROOT / "research/zenodo_7895795_jetfire_postaccess_diagnostic_2026_10_14.json")
        .read_text(encoding="utf-8")
    )
    assert artifact["status"] == "POST_ACCESS_THERMAL_PRESSURE_DIAGNOSTIC_NOT_INDEPENDENT_VALIDATION"
    assert artifact["source"]["dataset_doi"] == "10.5281/zenodo.7895795"
    assert artifact["source"]["actual_hydrogen"] is True
    assert artifact["provenance_boundary"]["independent_holdout"] is False
    assert artifact["provenance_boundary"]["prospective_validation"] is False
    assert artifact["provenance_boundary"]["parameter_fitting"] is False
    assert artifact["decision"]["gate_changed"] is False
    assert artifact["aggregate"]["workbook_count"] == 9
    assert artifact["aggregate"]["pressure_workbook_count"] == 9
    assert artifact["aggregate"]["free_jet_distance_trend_count"] == 2
    assert artifact["aggregate"]["free_jet_distance_trend_expected_decreasing_count"] == 2
