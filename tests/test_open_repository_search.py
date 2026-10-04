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
    assert item["source_count"] == 8
    assert item["gate_impact"] == "unchanged_independent_full_loop_gate_remains_open"
    assert "cal_state_la_cascade_2023_experiments" in item["source_ids"]
    assert "sunhydro_hsdc_operating_data" in item["source_ids"]


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


def test_external_search_mirror_contains_public_access_refresh():
    mirror = json.loads(
        (ROOT / "research/external_full_loop_data_search.json").read_text(
            encoding="utf-8"
        )
    )
    item = mirror["public_data_access_refresh_2026_10_04"]
    assert item["decision"] == "NO_NEW_ELIGIBLE_PUBLIC_RAW_FULL_LOOP_SET"
    assert any(
        source["id"] == "carb_2024_in_use_appendix_a_workbook"
        and source["public_artifact_inspection"]["public_workbook_or_raw_logger_found"] is False
        for source in item["sources"]
    )
    assert any(
        source["id"] == "threeemotion_operator_logbooks"
        and source["full_loop_holdout_eligible"] is False
        for source in item["sources"]
    )
    assert any(
        source["id"] == "bam_2026_data_driven_station"
        and source["public_artifact_inspection"]["raw_common_timebase_found"] is False
        for source in item["sources"]
    )


def test_public_data_access_refresh_keeps_carb_and_3emotion_out_of_holdout():
    record = json.loads(
        (ROOT / "research/public_data_access_refresh_2026_10_04.json").read_text(
            encoding="utf-8"
        )
    )
    assert record["decision"] == "NO_NEW_ELIGIBLE_PUBLIC_RAW_FULL_LOOP_SET"
    assert record["gate_impact"] == "unchanged_independent_full_loop_gate_remains_open"
    assert len(record["sources"]) == 4
    carb = next(source for source in record["sources"] if source["id"].startswith("carb_"))
    threeemotion = next(
        source for source in record["sources"] if source["id"] == "threeemotion_operator_logbooks"
    )
    assert carb["public_artifact_inspection"]["appendix_a_workbook_linked_from_report"] is False
    assert carb["full_loop_holdout_eligible"] is False
    assert threeemotion["public_artifact_inspection"]["raw_common_timebase_found"] is False
    assert threeemotion["full_loop_holdout_eligible"] is False
    bam = next(source for source in record["sources"] if source["id"] == "bam_2026_data_driven_station")
    assert bam["public_artifact_inspection"]["public_csv_xlsx_sql_found"] is False
    assert bam["full_loop_holdout_eligible"] is False
    zenodo = next(
        source
        for source in record["sources"]
        if source["id"] == "zenodo_chillerless_20183753_embedded_digitized_fills"
    )
    assert zenodo["public_artifact_inspection"]["embedded_fill_count"] == 9
    assert zenodo["full_loop_holdout_eligible"] is False
    assert (ROOT / "research/3EMOTION_DATA_REQUEST_DRAFT.md").exists()
    assert "written reuse rights" in record["claim_boundary"]


def test_figshare_recheck_keeps_station_full_loop_gate_open():
    record = json.loads(
        (ROOT / "research/figshare_h2_hrs_recheck_2026_10_04.json").read_text(
            encoding="utf-8"
        )
    )
    assert record["decision"] == "NO_NEW_ELIGIBLE_PUBLIC_RAW_SET"
    assert record["gate_impact"] == "unchanged_independent_full_loop_gate_remains_open"
    candidate = next(
        item for item in record["candidate_classifications"] if item["article_id"] == 27581394
    )
    assert candidate["license"] == "All rights reserved"
    assert candidate["decision"] == "PUBLIC_PUBLICATION_ONLY"
    assert all(
        item["decision"] != "NEW_INDEPENDENT_FULL_LOOP_HOLDOUT"
        for item in record["candidate_classifications"]
    )


def test_chinese_dispenser_article_tables_are_not_promoted_to_holdout():
    record = json.loads(
        (
            ROOT
            / "research/chinese_hrs_performance_article_recheck_2026_10_04.json"
        ).read_text(encoding="utf-8")
    )
    assert record["decision"] == "PUBLIC_SUMMARY_AND_TABLES_ONLY"
    assert record["gate_impact"] == "unchanged_independent_full_loop_gate_remains_open"
    assert len(record["linked_files"]) == 4
    assert all(item["time_series"] is False for item in record["linked_files"])
    assert record["reported_experiments"][1]["duration_s"] == 276


def test_calstate_public_data_lead_requires_custodian_export():
    record = json.loads(
        (ROOT / "research/calstate_la_public_data_leads_2026_10_04.json").read_text(
            encoding="utf-8"
        )
    )
    assert record["decision"] == "HIGH_VALUE_DATA_REQUEST_LEAD_NO_PUBLIC_RAW_ARCHIVE"
    assert record["gate_impact"] == "unchanged_independent_full_loop_gate_remains_open"
    assert any(
        item["id"] == "calstate_2021_back_to_back_article"
        and item["decision"] == "DATA_REQUEST_LEAD"
        for item in record["sources"]
    )
    assert all(
        item.get("decision") != "NEW_INDEPENDENT_FULL_LOOP_HOLDOUT"
        for item in record["sources"]
    )
