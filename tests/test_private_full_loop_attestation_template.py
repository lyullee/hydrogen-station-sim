import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_private_full_loop_attestation_template_is_privacy_bounded_and_complete():
    path = ROOT / "research" / "PRIVATE_FULL_LOOP_ATTESTATION_TEMPLATE_2026_10_11.json"
    document = json.loads(path.read_text(encoding="utf-8"))

    privacy = document["privacy_boundary"]
    assert privacy["raw_rows_in_repository"] is False
    assert privacy["site_or_company_identity_in_repository"] is False
    assert privacy["exact_dates_in_repository"] is False
    assert privacy["equipment_manufacturer_or_serials_in_repository"] is False

    required_roles = {
        item["role"]
        for item in document["channel_attestations"]
        if item.get("required")
    }
    assert required_roles == {
        "common_time",
        "station_pressure",
        "delivered_temperature",
        "mass_flow",
        "cascade_or_storage",
        "vehicle_identity",
        "vehicle_pressure",
        "vehicle_temperature",
        "controller_state",
    }
    assert document["holdout_controls"]["minimum_independent_events"] >= 3
    assert document["admission_rule"]["missing_role_blocks_holdout"] is True

