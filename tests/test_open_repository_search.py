import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_open_repository_recheck_keeps_full_loop_claim_boundary():
    record = json.loads(
        (ROOT / "research/open_repository_search_2026_10_04.json").read_text(
            encoding="utf-8"
        )
    )
    assert record["decision"] == "NO_NEW_ELIGIBLE_PUBLIC_RAW_SET"
    assert record["gate_impact"] == "unchanged_independent_full_loop_gate_remains_open"
    assert len(record["zenodo_api_recheck"]["queries"]) >= 5
    assert any(
        candidate["record_id"] == "22892319"
        and candidate["decision"] == "PUBLIC_PUBLICATION_ONLY"
        for candidate in record["zenodo_api_recheck"]["candidate_classifications"]
    )
    assert any(
        item["doi"] == "10.17632/8km9z62tct.1"
        and item["decision"] == "COMPONENT_STORAGE_TANK_ONLY"
        for item in record["public_repository_followups"]
    )
    assert "No candidate is promoted" in record["claim_boundary"]


def test_external_search_mirror_contains_same_recheck_decision():
    mirror = json.loads(
        (ROOT / "research/external_full_loop_data_search.json").read_text(
            encoding="utf-8"
        )
    )
    assert mirror["last_reviewed"] == "2026-10-04"
    assert mirror["zenodo_api_and_mendeley_recheck_2026_10_04"]["decision"] == (
        "NO_NEW_ELIGIBLE_PUBLIC_RAW_SET"
    )


def test_external_search_mirror_contains_cal_state_la_recheck():
    mirror = json.loads(
        (ROOT / "research/external_full_loop_data_search.json").read_text(
            encoding="utf-8"
        )
    )
    item = mirror["cal_state_la_hrff_public_data_recheck_2026_10_04"]
    assert item["decision"] == (
        "HIGH_VALUE_REAL_HRS_CANDIDATES_NO_PUBLIC_RAW_LOGGER_FOUND"
    )
    assert item["sources"][1]["full_loop_holdout_eligible"] is False


def test_external_search_mirror_contains_preslhy_e3_5_recheck():
    mirror = json.loads(
        (ROOT / "research/external_full_loop_data_search.json").read_text(
            encoding="utf-8"
        )
    )
    item = mirror["preslhy_e3_5_public_data_recheck_2026_10_04"]
    assert item["decision"] == "PUBLIC_RAW_CONSEQUENCE_CANDIDATE_METADATA_VERIFIED"
    assert item["archive_not_vendored"] is True
    assert item["archive_size_bytes"] == 11341115392


def test_external_search_mirror_contains_hrs_public_data_recheck():
    mirror = json.loads(
        (ROOT / "research/external_full_loop_data_search.json").read_text(
            encoding="utf-8"
        )
    )
    item = mirror["hrs_public_data_recheck_2026_10_04"]
    assert item["decision"] == (
        "PUBLIC_AGGREGATE_AND_EXPERIMENT_SUMMARIES_CONFIRMED_NO_NEW_FULL_LOOP_RAW"
    )
    assert item["source_count"] == 6
    assert item["gate_impact"] == "unchanged_independent_full_loop_gate_remains_open"


def test_external_search_mirror_contains_primary_source_context_refresh():
    mirror = json.loads(
        (ROOT / "research/external_full_loop_data_search.json").read_text(
            encoding="utf-8"
        )
    )
    item = mirror["public_station_context_refresh_2026_10_04"]
    assert item["decision"] == "NO_NEW_ELIGIBLE_PUBLIC_RAW_FULL_LOOP_SET"
    assert any(
        source["id"] == "cal_state_la_back_to_back_accepted_manuscript"
        and source["decision"] == "HIGH_VALUE_DATA_REQUEST_LEAD"
        for source in item["sources"]
    )
    assert "full-loop numerical gate remains open" in item["result"]
