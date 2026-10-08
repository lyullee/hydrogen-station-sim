from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "research/local_public_validation_catalog_2026_10_09.json"


def test_catalog_is_privacy_bounded_and_non_eligibility_claiming() -> None:
    record = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    assert record["artifact_type"] == "local_public_validation_catalog"
    assert record["status"] == "privacy_bounded_catalog_only"
    assert all(value is False for value in record["privacy"].values())
    assert record["scope"]["collection_count"] > 10
    assert record["scope"]["file_count"] > 100
    assert record["coverage_assessment"]["new_full_loop_cohort_identified_by_catalog"] is False
    assert record["coverage_assessment"]["full_loop_holdout_eligible"] is False
    assert all(
        item["full_loop_holdout_eligible"] is False
        and item["decision"] == "CATALOG_ONLY_REQUIRES_DATASET_SPECIFIC_VALIDATION"
        for item in record["collections"]
    )


def test_catalog_contains_the_public_station_and_consequence_families() -> None:
    record = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    families = {item["family_hint"] for item in record["collections"]}
    assert "tank_and_refueling_measurements" in families
    assert "dispersion_or_detector_component" in families
    assert "refueling_protocol_or_controller_cases" in families
