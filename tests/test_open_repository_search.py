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
    assert record["pdf_file_level_inspection"]["embedded_files"] == []
    assert record["pdf_file_level_inspection"]["external_links"] == []
    assert all(
        item.get("decision") != "NEW_INDEPENDENT_FULL_LOOP_HOLDOUT"
        for item in record["sources"]
    )


def test_methytrucks_public_workbooks_are_quarantined_as_auxiliary_only():
    record = json.loads(
        (
            ROOT
            / "research/metHyTrucks_public_measurement_recheck_2026_10_04.json"
        ).read_text(encoding="utf-8")
    )
    assert record["decision"] == "PUBLIC_RAW_HRS_SAMPLING_TIME_SERIES_AUXILIARY_ONLY"
    assert record["gate_impact"] == "unchanged_independent_full_loop_gate_remains_open"
    assert record["file_level_inspection"]["file_count"] == 13
    assert record["classification"]["full_loop_holdout_eligible"] is False
    assert record["classification"]["station_measurement_auxiliary_eligible"] is True
    assert all(item["sampling_interval_observed_s"] == 0.5 for item in record["file_level_inspection"]["files"])
    assert "vehicle/receptacle loop" in record["claim_boundary"]


def test_external_search_mirror_contains_methytrucks_recheck():
    mirror = json.loads(
        (ROOT / "research/external_full_loop_data_search.json").read_text(
            encoding="utf-8"
        )
    )
    item = mirror["methytrucks_zenodo_measurement_recheck_2026_10_04"]
    assert item["full_loop_holdout_eligible"] is False
    assert item["station_measurement_auxiliary_eligible"] is True


def test_primary_source_search_refresh_keeps_full_loop_gate_open():
    record = json.loads(
        (
            ROOT
            / "research/public_full_loop_search_refresh_2026_10_04.json"
        ).read_text(encoding="utf-8")
    )
    assert record["decision"] == "NO_NEW_ELIGIBLE_PUBLIC_RAW_FULL_LOOP_SET"
    assert record["gate_impact"] == "unchanged_independent_full_loop_gate_remains_open"
    assert len(record["sources"]) == 5
    assert all(source["full_loop_holdout_eligible"] is False for source in record["sources"])
    assert any(
        source["id"] == "kuroki_2023_hitrf_liner_temperature"
        and source["data_availability"] == "Research data are not shared"
        for source in record["sources"]
    )
    assert any(
        source["id"] == "nrel_nfctec_secure_data_center"
        and source["raw_common_timebase_found"] is False
        for source in record["sources"]
    )


def test_external_search_mirror_contains_primary_source_search_refresh():
    mirror = json.loads(
        (ROOT / "research/external_full_loop_data_search.json").read_text(
            encoding="utf-8"
        )
    )
    item = mirror["public_full_loop_search_refresh_2026_10_04"]
    assert item["full_loop_holdout_eligible"] is False
    assert len(item["source_ids"]) == 5
    assert "nist_transient_flow_facility_refresh" in item["source_ids"]


def test_mc_default_source_boundary_diagnostic_is_explicitly_non_validating():
    record = json.loads(
        (
            ROOT
            / "research/mc_default_source_boundary_identifiability_2026_10_04.json"
        ).read_text(encoding="utf-8")
    )
    assert record["status"] == "DEVELOPMENT_DIAGNOSTIC_ONLY"
    assert len(record["cases"]) == 8
    assert record["validation_boundary"]["full_loop_holdout_eligible"] is False
    assert record["validation_boundary"]["frozen_holdout_modified"] is False
    assert record["validation_boundary"]["post_outcome_tuning"] is False
    assert all(
        row["observed_source_pressure_drop_mpa"] > 0.0
        and row["conditional_implied_constant_volume_m3"] > 0.0
        for row in record["cases"]
    )
    assert min(
        row["conditional_implied_constant_volume_m3"] for row in record["cases"]
    ) > record["method"]["reference_volume_m3"]


def test_external_search_mirror_contains_source_boundary_diagnostic():
    mirror = json.loads(
        (ROOT / "research/external_full_loop_data_search.json").read_text(
            encoding="utf-8"
        )
    )
    item = mirror["mc_default_source_boundary_identifiability_2026_10_04"]
    assert item["decision"] == "DEVELOPMENT_DIAGNOSTIC_ONLY"
    assert item["cases"] == 8
    assert item["full_loop_holdout_eligible"] is False


def test_measured_boundary_diagnostic_retains_negative_joint_screen():
    record = json.loads(
        (ROOT / "research/mc_measured_boundary_diagnostic_2026_10_05.json").read_text(
            encoding="utf-8"
        )
    )
    assert record["evidence_role"] == "DEVELOPMENT_DIAGNOSTIC_ONLY"
    assert record["post_outcome"] is True
    assert record["parameter_fitting"] is False
    assert record["case_count"] == 8
    assert len(record["runs"]) == 4
    assert record["validation_boundary"]["full_loop_holdout_eligible"] is False
    assert record["validation_boundary"]["goal_completion_permitted"] is False
    assert max(run["aggregate"]["screening_pass_count"] for run in record["runs"]) == 1
    assert all(
        run["aggregate"]["temperature_rmse_c"] > record["protocol"]["screening_limits"]["temperature_rmse_c"]
        for run in record["runs"]
    )


def test_external_search_mirror_contains_measured_boundary_diagnostic():
    mirror = json.loads(
        (ROOT / "research/external_full_loop_data_search.json").read_text(
            encoding="utf-8"
        )
    )
    item = mirror["mc_measured_boundary_diagnostic_2026_10_05"]
    assert item["decision"] == "DEVELOPMENT_DIAGNOSTIC_ONLY"
    assert item["case_count"] == 8
    assert item["best_screening_pass_count"] == 1
    assert item["full_loop_holdout_eligible"] is False


def test_frozen_boundary_vehicle_diagnostic_retains_negative_screen():
    record = json.loads(
        (
            ROOT
            / "research/mc_default_frozen_boundary_vehicle_diagnostic_2026_10_04.json"
        ).read_text(encoding="utf-8")
    )
    assert record["status"] == "DEVELOPMENT_DIAGNOSTIC_ONLY"
    assert record["protocol"]["fresh_holdout"] is False
    assert record["protocol"]["source_pressure_boundary"] == "published source_pressure_3_mpa trace"
    assert record["protocol"]["case_count"] == 8
    assert record["validation_boundary"]["full_loop_holdout_eligible"] is False
    assert record["validation_boundary"]["goal_completion_permitted"] is False
    assert sum(bool(row["screening_pass"]) for row in record["cases"]) == 1
    assert record["aggregate"]["temperature_rmse_c"] > record["screening_limits"]["temperature_rmse_c"]
    assert record["aggregate"]["soc_rmse_percentage_points"] > record["screening_limits"]["soc_final_abs_error_percentage_points"]


def test_release_validation_failure_diagnosis_keeps_negative_claim_boundary():
    record = json.loads(
        (
            ROOT
            / "research/release_validation_failure_diagnosis_2026_10_04.json"
        ).read_text(encoding="utf-8")
    )
    assert record["status"] == "DEVELOPMENT_DIAGNOSTIC_ONLY"
    assert record["validation_boundary"]["frozen_holdouts_modified"] is False
    assert record["validation_boundary"]["post_outcome_parameter_fitting"] is False
    assert record["validation_boundary"]["goal_completion_permitted"] is False
    assert record["validation_boundary"]["claim_supported"] is False
    assert record["implementation_review"]["clear_unit_or_initial_condition_bug_found"] is False
    assert record["frozen_results"]["proust"]["joint_primary_pass_fraction"] == 0.0
    assert record["frozen_results"]["schefer_2006"]["joint_primary_pass"] is False
    assert record["frozen_results"]["schefer_2007"]["joint_primary_pass"] is False
    assert record["development_only_evidence"]["promotion_blocked"] is True


def test_public_full_loop_search_addendum_keeps_new_leads_quarantined():
    record = json.loads(
        (
            ROOT
            / "research/public_full_loop_search_addendum_2026_10_04.json"
        ).read_text(encoding="utf-8")
    )
    assert record["decision"] == "NO_NEW_ELIGIBLE_PUBLIC_RAW_FULL_LOOP_SET"
    assert record["gate_impact"] == "unchanged_independent_full_loop_gate_remains_open"
    assert len(record["sources"]) == 6
    assert all(source["full_loop_holdout_eligible"] is False for source in record["sources"])
    nbsdc = next(
        source
        for source in record["sources"]
        if source["id"] == "nbsdc_beijing_winter_olympics_hrs_operational_addendum"
    )
    assert nbsdc["raw_file_access"] == "approval_required"
    assert nbsdc["common_timebase_and_vehicle_mapping_verified"] is False
    deng = next(
        source
        for source in record["sources"]
        if source["id"] == "deng_2025_high_flow_refueling_tank_addendum"
    )
    assert deng["raw_common_timebase_found"] is False
    assert (ROOT / "research/DENG_2025_HIGH_FLOW_DATA_REQUEST_DRAFT.md").exists()
    calstate = next(
        source
        for source in record["sources"]
        if source["id"] == "calstate_genovese_2021_in_situ_fueling_addendum"
    )
    assert calstate["public_raw_data"] is False
    assert (ROOT / "research/CALSTATE_DATA_REQUEST_DRAFT.md").exists()
    bam = next(
        source
        for source in record["sources"]
        if source["id"] == "bam_kim_2026_field_monitoring_addendum"
    )
    assert bam["public_raw_data"] is False
    assert (ROOT / "research/BAM_HRS_DATA_REQUEST_DRAFT.md").exists()
    threeemotion = next(
        source
        for source in record["sources"]
        if source["id"] == "threeemotion_2022_operational_addendum"
    )
    assert threeemotion["aggregation_level"] == "daily/event log summaries"
    assert threeemotion["raw_common_timebase_verified"] is False


def test_external_search_mirror_contains_public_full_loop_search_addendum():
    mirror = json.loads(
        (ROOT / "research/external_full_loop_data_search.json").read_text(
            encoding="utf-8"
        )
    )
    item = mirror["public_full_loop_search_addendum_2026_10_04"]
    assert item["decision"] == "NO_NEW_ELIGIBLE_PUBLIC_RAW_FULL_LOOP_SET"
    assert item["full_loop_holdout_eligible"] is False
    assert len(item["source_ids"]) == 6
    assert "calstate_genovese_2021_in_situ_fueling_addendum" in item["source_ids"]
    assert "bam_kim_2026_field_monitoring_addendum" in item["source_ids"]
    assert "threeemotion_2022_operational_addendum" in item["source_ids"]


def test_fts_recheck_records_public_traces_without_promoting_pseudo_raw_data():
    record = json.loads(
        (
            ROOT
            / "research/public_full_loop_search_fts_recheck_2026_10_04.json"
        ).read_text(encoding="utf-8")
    )
    assert record["decision"] == "NO_NEW_ELIGIBLE_PUBLIC_RAW_FULL_LOOP_SET"
    assert record["gate_impact"] == "unchanged_independent_full_loop_gate_remains_open"
    assert len(record["sources"]) == 5
    assert all(source["full_loop_holdout_eligible"] is False for source in record["sources"])
    nist = next(source for source in record["sources"] if source["id"] == "nist_fts_tn1888_public_artifact_check")
    assert nist["public_artifact_inspection"]["published_pdf_found"] is True
    assert nist["public_artifact_inspection"]["machine_readable_logger_archive_found"] is False
    nrel = next(source for source in record["sources"] if source["id"] == "nrel_h2iq_2024_heavy_duty_public_trace_check")
    assert nrel["public_artifact_inspection"]["public_raw_logger_found"] is False
    mc = next(source for source in record["sources"] if source["id"] == "h2protocol_mc_default_public_archive_rights_recheck")
    assert mc["public_artifact_inspection"]["machine_readable_bench_archive_found"] is True
    assert mc["public_artifact_inspection"]["written_open_data_license_found"] is False


def test_external_search_mirror_contains_fts_recheck():
    mirror = json.loads(
        (ROOT / "research/external_full_loop_data_search.json").read_text(
            encoding="utf-8"
        )
    )
    item = mirror["public_full_loop_search_fts_recheck_2026_10_04"]
    assert item["decision"] == "NO_NEW_ELIGIBLE_PUBLIC_RAW_FULL_LOOP_SET"
    assert item["full_loop_holdout_eligible"] is False
    assert "nist_fts_tn1888_public_artifact_check" in item["source_ids"]
    assert "nrel_h2iq_2024_heavy_duty_public_trace_check" in item["source_ids"]


def test_khk_incident_database_access_is_local_only_and_not_promoted():
    record = json.loads(
        (ROOT / "research/khk_public_incident_access_2026_10_04.json").read_text(
            encoding="utf-8"
        )
    )
    assert record["access_status"] == "LOCAL_ARCHIVE_READABLE"
    assert record["local_archive"]["gitignored"] is True
    assert record["local_archive"]["committed_or_redistributed"] is False
    assert record["rights_and_restrictions"]["public_posting_or_public_download_mirror_prohibited"] is True
    assert record["validation_classification"]["accident_casebook_candidate_for_local_saga_grounding"] is True
    assert record["validation_classification"]["full_loop_station_vehicle_holdout_eligible"] is False
    assert record["validation_classification"]["goal_completion_permitted"] is False
    assert (ROOT / "research/KHK_DATA_PERMISSION_REQUEST_DRAFT.md").exists()


def test_elvhys_dataset_is_cc0_consequence_auxiliary_only():
    record = json.loads(
        (
            ROOT
            / "research/elvhys_public_consequence_dataset_2026_10_04.json"
        ).read_text(encoding="utf-8")
    )
    assert record["license"] == "CC0 1.0"
    assert record["reported_test_count"] == 48
    assert record["file_count"] == 198
    assert record["classification"]["public_consequence_auxiliary_eligible"] is True
    assert record["classification"]["full_loop_station_vehicle_holdout_eligible"] is False
    assert record["classification"]["goal_completion_permitted"] is False
    assert (ROOT / "research/ELVHYS_PUBLIC_CONSEQUENCE_DATASET.md").exists()


def test_dlr_fch2rail_measurement_lead_is_not_promoted_without_raw_logger():
    record = json.loads(
        (ROOT / "research/public_full_loop_search_recheck_2026_10_05.json").read_text(
            encoding="utf-8"
        )
    )
    item = next(
        source for source in record["candidates"]
        if source["id"] == "fch2rail_dlr_ijhe_2025_raw_check"
    )
    assert item["observed_scope"]["public_raw_logger_retrieved"] is False
    assert item["observed_scope"]["full_loop_holdout_eligible"] is False
    assert item["decision"] == "REAL_STATION_DATA_REQUEST_LEAD_NO_RAW_ARCHIVE"


def test_khk_local_casebook_pipeline_is_not_promoted_or_committed():
    mirror = json.loads(
        (ROOT / "research/external_full_loop_data_search.json").read_text(
            encoding="utf-8"
        )
    )
    item = mirror["khk_local_casebook_pipeline_2026_10_04"]
    assert item["raw_or_derived_casebook_committed"] is False
    assert item["expert_holdout_ready"] is False
    assert item["full_loop_holdout_eligible"] is False
    assert (ROOT / "research/KHK_LOCAL_CASEBOOK_PROTOCOL.md").exists()
