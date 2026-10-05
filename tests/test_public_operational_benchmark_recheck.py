import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_operational_benchmark_recheck_preserves_raw_trace_boundary():
    record = json.loads(
        (ROOT / "research/public_operational_benchmark_recheck_2026_10_05.json")
        .read_text(encoding="utf-8")
    )
    assert record["result"] == "NO_NEW_ELIGIBLE_PUBLIC_RAW_FULL_LOOP_SET"
    assert record["gate_impact"] == "full_loop_external_validation_remains_open"
    assert len(record["candidates"]) == 15
    assert all(
        item["decision"] != "FULL_LOOP_HOLDOUT" for item in record["candidates"]
    )
    required = set(record["eligibility_boundary"]["full_loop_required_channels"])
    assert required == {
        "common elapsed time or timestamp",
        "vehicle or receptacle pressure",
        "mass flow or transferred mass",
    }


def test_recheck_explicitly_contains_real_station_but_non_raw_sources():
    record = json.loads(
        (ROOT / "research/public_operational_benchmark_recheck_2026_10_05.json")
        .read_text(encoding="utf-8")
    )
    real_station = [
        item for item in record["candidates"]
        if item["id"] in {
            "calstate_la_multi_year_ijhe_2023",
            "calstate_la_back_to_back_jclepro_2021",
            "uci_nfcrc_early_hrs_ijhe_2020",
        }
    ]
    assert len(real_station) == 3
    assert all("request" in item["use"].lower() for item in real_station)


def test_recheck_excludes_public_simulation_supplement_from_physical_holdout():
    record = json.loads(
        (ROOT / "research/public_operational_benchmark_recheck_2026_10_05.json")
        .read_text(encoding="utf-8")
    )
    item = next(
        candidate for candidate in record["candidates"]
        if candidate["id"] == "upc_onsite_hrs_supplementary_simulation_2024"
    )
    assert item["decision"] == "SIMULATION_SUPPLEMENTARY_EXCLUDED"
    assert item["observed_scope"]["measured_station_logger_rows"] is False


def test_recheck_records_bam_keti_field_article_without_promoting_it_to_raw_holdout():
    record = json.loads(
        (ROOT / "research/public_operational_benchmark_recheck_2026_10_05.json")
        .read_text(encoding="utf-8")
    )
    item = next(
        candidate for candidate in record["candidates"]
        if candidate["id"] == "bam_keti_hrs_anomaly_platform_2026"
    )
    assert item["decision"] == "REAL_STATION_FIELD_VALIDATION_AND_DATA_REQUEST_LEAD"
    assert item["observed_scope"]["reported_sensor_count"] == 8
    assert "raw logger" in item["finding"]


def test_recheck_records_calstate_back_to_back_campaign_without_promoting_it_to_raw_holdout():
    record = json.loads(
        (ROOT / "research/public_operational_benchmark_recheck_2026_10_05.json")
        .read_text(encoding="utf-8")
    )
    item = next(
        candidate for candidate in record["candidates"]
        if candidate["id"] == "calstate_la_back_to_back_jclepro_2021"
    )
    assert item["decision"] == "REAL_STATION_AGGREGATE_AND_DATA_REQUEST_LEAD"
    assert item["observed_scope"]["raw_synchronized_rows"] is False
    assert "logger archive" in item["finding"]


def test_recheck_records_carb_field_report_without_promoting_it_to_raw_holdout():
    record = json.loads(
        (ROOT / "research/public_operational_benchmark_recheck_2026_10_05.json")
        .read_text(encoding="utf-8")
    )
    item = next(
        candidate for candidate in record["candidates"]
        if candidate["id"] == "carb_2024_light_duty_in_use_study"
    )
    assert item["decision"] == "REAL_STATION_TEST_REPORT_ONLY"
    assert item["observed_scope"]["raw_synchronized_rows"] is False
    assert "dispenser data logs" in item["finding"]


def test_recheck_records_ramea_capacity_archive_as_aggregate_only():
    record = json.loads(
        (ROOT / "research/public_operational_benchmark_recheck_2026_10_05.json")
        .read_text(encoding="utf-8")
    )
    item = next(
        candidate for candidate in record["candidates"]
        if candidate["id"] == "ramea_2019_public_capacity_repository_2026"
    )
    assert item["decision"] == "PUBLIC_AGGREGATE_STATION_CAPACITY_CONTEXT_ONLY"
    assert item["observed_scope"]["station_directories"] == 36
    assert item["observed_scope"]["csv_files"] == 2563
    assert item["observed_scope"]["raw_synchronized_vehicle_trace"] is False
    assert "explicit reuse license" in item["finding"]


def test_recheck_records_hysafe_real_experiment_as_figure_only_data_request_lead():
    record = json.loads(
        (ROOT / "research/public_operational_benchmark_recheck_2026_10_05.json")
        .read_text(encoding="utf-8")
    )
    item = next(
        candidate for candidate in record["candidates"]
        if candidate["id"] == "hysafe_volume_estimation_2026_10_05"
    )
    assert item["decision"] == "REAL_STATION_EXPERIMENT_FIGURE_ONLY_DATA_REQUEST_LEAD"
    assert item["observed_scope"]["reported_tests"] == 14
    assert item["observed_scope"]["raw_synchronized_rows"] is False
    assert "no additional external datasets" in item["observed_scope"]["data_availability_statement"].lower()


def test_recheck_records_chinese_35_70_mpa_field_experiments_as_table_only_lead():
    record = json.loads(
        (ROOT / "research/public_operational_benchmark_recheck_2026_10_05.json")
        .read_text(encoding="utf-8")
    )
    item = next(
        candidate for candidate in record["candidates"]
        if candidate["id"] == "cip_chinese_35_70mpa_station_experiments_2020"
    )
    assert item["decision"] == "REAL_STATION_EXPERIMENT_TABLE_ONLY_DATA_REQUEST_LEAD"
    assert item["observed_scope"]["reported_cases"] == 2
    assert item["observed_scope"]["raw_synchronized_rows"] is False
    assert item["observed_scope"]["case_70_mpa"]["peak_mass_flow_g_s"] == 36.0


def test_recheck_records_calstate_experimental_comparison_without_raw_holdout():
    record = json.loads(
        (ROOT / "research/public_operational_benchmark_recheck_2026_10_05.json")
        .read_text(encoding="utf-8")
    )
    item = next(candidate for candidate in record["candidates"] if candidate["id"] == "calstate_la_cascade_direct_energies_2023")
    assert item["decision"] == "REAL_STATION_EXPERIMENT_FIGURE_ONLY_DATA_REQUEST_LEAD"
    assert item["observed_scope"]["reported_cases"] == 3
    assert item["observed_scope"]["raw_synchronized_rows"] is False
    assert "logger archive" in item["finding"]


def test_recheck_records_fch2rail_synchronized_channel_boundary():
    record = json.loads(
        (ROOT / "research/public_operational_benchmark_recheck_2026_10_05.json")
        .read_text(encoding="utf-8")
    )
    item = next(candidate for candidate in record["candidates"] if candidate["id"] == "fch2rail_hrs_train_refueling_ijhe_2025")
    assert item["doi"] == "10.1016/j.ijhydene.2025.04.040"
    assert item["observed_scope"]["raw_synchronized_rows"] is False
    assert "raw export" in item["use"]
