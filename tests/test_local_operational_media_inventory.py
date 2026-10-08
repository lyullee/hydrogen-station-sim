"""Regression checks for the privacy-bounded local operational-media screen."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "research/local_operational_media_inventory_2026_10_09.json"
ASSET_SCREEN = ROOT / "research/local_station_asset_screen_2026_10_09.json"


def test_operational_media_inventory_is_privacy_bounded() -> None:
    record = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    privacy = record["privacy"]
    assert privacy["source_paths_published"] is False
    assert privacy["source_filenames_published"] is False
    assert privacy["source_timestamps_published"] is False
    assert privacy["raw_media_persisted"] is False
    assert privacy["frames_published"] is False
    assert privacy["site_company_manufacturer_published"] is False


def test_operational_media_inventory_preserves_metadata_only_boundary() -> None:
    record = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    collection = record["collection"]
    screen = collection["container_metadata_screen"]
    assert collection["file_count"] == 26
    assert screen["complete_container_count"] == 17
    assert screen["incomplete_or_unreadable_container_count"] == 9
    assert screen["video_dimensions"] == "1920x1080 for all complete video tracks"
    assert "process telemetry or sensor calibration" in record["ineligible_use"]
    assert "consequence-distance validation or automatic safety-limit generation" in record[
        "ineligible_use"
    ]


def test_station_asset_screen_records_visual_media_without_closing_validation_gate() -> None:
    record = json.loads(ASSET_SCREEN.read_text(encoding="utf-8"))
    bundle = next(
        item
        for item in record["station_specific_bundles"]
        if item["id"] == "local_operational_video_collection"
    )
    assert bundle["file_count"] == 26
    assert bundle["complete_container_count"] == 17
    assert bundle["incomplete_or_unreadable_container_count"] == 9
    coverage = record["coverage_assessment"]
    assert coverage["local_operational_visual_evidence_is_substantial"] is True
    assert coverage["local_operational_visual_evidence_is_quantitatively_validated"] is False
    assert coverage["vehicle_side_full_loop_validation_ready"] is False
