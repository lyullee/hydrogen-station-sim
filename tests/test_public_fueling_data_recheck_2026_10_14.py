from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RECHECK = ROOT / "research" / "public_fueling_data_recheck_2026_10_14.json"


def test_public_fueling_recheck_is_fail_closed() -> None:
    payload = json.loads(RECHECK.read_text(encoding="utf-8"))

    assert payload["result"] == (
        "NO_NEW_PUBLIC_SYNCHRONIZED_STATION_TO_VEHICLE_HOLDOUT_ADMITTED"
    )
    assert payload["scope_effect"].startswith("Keep full-loop external validation")
    assert payload["next_action"].startswith("Request a rights-cleared")

    decisions = {item["id"]: item["decision"] for item in payload["candidates"]}
    assert decisions["jrc_gastef_reference_data"] == "CONTACT_REQUEST_CANDIDATE_ONLY"
    assert decisions["kuroki_hitrf_36l"] == "PUBLISHED_EXPERIMENT_DESCRIPTION_DATA_NOT_SHARED"
    assert decisions["nrel_h2fills_hdvs"] == "PARTIAL_TANK_BOUNDARY_ONLY"
    assert decisions["nrel_retail_composite_products"] == "CONTEXT_ONLY"
    assert decisions["nist_hydrogen_field_test_standard"] == "CONTACT_REQUEST_CANDIDATE_ONLY"
