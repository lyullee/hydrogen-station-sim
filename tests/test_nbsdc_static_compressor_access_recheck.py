from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_nbsdc_static_compressor_access_recheck_is_metadata_only():
    record = json.loads(
        (ROOT / "research/nbsdc_static_compressor_access_recheck_2026_10_12.json")
        .read_text(encoding="utf-8")
    )
    assert record["source"]["data_id"] == "64edc6babb16e07753c3461a"
    inventory = record["metadata_observation"]["numerical_group"]
    assert inventory["numerical_file_count"] == 7
    assert inventory["origin_project_file_count"] == 7
    assert record["raw_file_probe"]["portal_code"] == 403
    assert record["raw_file_probe"]["raw_bytes_received"] is False
    assert record["paper_admission"]["numerical_validation_eligible"] is False


def test_nbsdc_static_compressor_source_catalogue_points_to_recheck():
    catalog = json.loads((ROOT / "research/data_sources.json").read_text(encoding="utf-8"))
    source = catalog["sources"]["nbsdc_static_hydrogen_compression_test_dataset_2026_10_12"]
    assert source["public_raw_data"] is False
    assert source["access_recheck"].endswith(
        "nbsdc_static_compressor_access_recheck_2026_10_12.json"
    )
