"""The public ELVHYS archive is traceable but remains consequence-component evidence."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_elvhys_dataverse_manifest_and_rights_are_recorded():
    record = json.loads(
        (ROOT / "research/elvhys_dataverse_metadata_audit_2026_10_05.json")
        .read_text(encoding="utf-8")
    )
    assert record["source"]["doi"] == "10.18710/JXJP0H"
    assert record["source"]["license"] == "CC0 1.0"
    assert record["source"]["public_access"] is True
    assert record["archive_manifest"]["file_count"] == 198
    assert record["archive_manifest"]["category_counts"] == {
        "CONC": 40,
        "FLMT": 35,
        "PRES": 40,
        "TEMP": 40,
        "MISC": 40,
        "README": 1,
        "META": 1,
        "SENSOR_DETAILS_PDF": 1,
    }
    assert record["experimental_scope"]["reported_test_count"] == 48
    assert (
        record["experimental_scope"]["date_consistency"]
        == "CONFLICT_REQUIRES_CITATION_CLARIFICATION"
    )


def test_elvhys_is_not_promoted_to_full_loop_or_goal_completion():
    record = json.loads(
        (ROOT / "research/elvhys_dataverse_metadata_audit_2026_10_05.json")
        .read_text(encoding="utf-8")
    )
    eligibility = record["eligibility"]
    assert eligibility["public_consequence_component_eligible"] is True
    assert eligibility["full_loop_station_vehicle_holdout_eligible"] is False
    assert eligibility["gaseous_h70_station_transfer_eligible"] is False
    assert eligibility["goal_completion_permitted"] is False
    samples = record["file_level_checks"]["sample_file_manifest"]
    assert len(samples) == 4
    assert all(item["rows"] > 0 and item["md5"] for item in samples)
