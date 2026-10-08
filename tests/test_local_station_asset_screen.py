"""Regression checks for the privacy-bounded local station asset inventory."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "research/local_station_asset_screen_2026_10_09.json"


def test_local_station_asset_screen_is_privacy_bounded() -> None:
    record = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    privacy = record["privacy"]
    assert privacy["source_paths_published"] is False
    assert privacy["source_filenames_published"] is False
    assert privacy["source_headers_published"] is False
    assert privacy["raw_rows_persisted"] is False
    assert privacy["site_company_manufacturer_published"] is False


def test_local_station_asset_screen_preserves_station_side_and_full_loop_boundary() -> None:
    record = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    coverage = record["coverage_assessment"]
    assert coverage["local_station_data_is_sparse"] is False
    assert coverage["station_side_dynamic_evidence_is_substantial"] is True
    assert coverage["local_hazop_scenario_coverage_is_substantial"] is True
    assert coverage["vehicle_side_full_loop_validation_ready"] is False
    assert coverage["quantitative_consequence_validation_ready"] is False


def test_local_scenario_matrix_has_actionable_but_nonquantitative_scope() -> None:
    record = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    matrix = next(
        item
        for item in record["station_specific_bundles"]
        if item["id"] == "local_liquid_hydrogen_operational_scenario_matrix"
    )
    assert matrix["scenario_step_rows"] == 52
    assert matrix["nonempty_consequence_fields"]["leak"] == 52
    assert matrix["nonempty_consequence_fields"]["fire"] == 52
    assert matrix["nonempty_consequence_fields"]["explosion"] == 52
    assert "incident frequency estimation" in matrix["ineligible_use"]
