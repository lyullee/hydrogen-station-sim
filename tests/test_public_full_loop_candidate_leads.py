import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_candidate_leads_do_not_relax_full_loop_gate() -> None:
    path = ROOT / "research/public_full_loop_candidate_leads_2026_10_10.json"
    record = json.loads(path.read_text(encoding="utf-8"))

    assert record["artifact_type"] == "public_full_loop_candidate_leads"
    assert record["decision"]["new_full_loop_dataset_admitted"] is False
    assert record["decision"]["runtime_parameter_application"] is False
    assert record["decision"]["goal_completion_permitted"] is False
    bam = next(item for item in record["candidates"] if item["id"].startswith("bam_"))
    assert bam["admission_status"] == "CONTACT_REQUEST_CANDIDATE_ONLY"
    assert bam["full_loop_external_holdout_eligible"] is False
    draft = ROOT / "research/BAM_KETI_DATA_REQUEST_DRAFT_2026_10_10.md"
    assert draft.is_file()
    assert "staged privacy-safe request" in bam["next_action"]
    nrel = next(item for item in record["candidates"] if item["id"].startswith("nrel_"))
    assert nrel["admission_status"] == "PARTIAL_STATION_TO_TANK_BOUNDARY_ONLY"
    assert nrel["full_loop_external_holdout_eligible"] is False
    dlr = next(
        item for item in record["candidates"]
        if item["id"] == "dlr_rail_h2_refueling_measurement_2025"
    )
    assert dlr["admission_status"] == "CONTACT_REQUEST_CANDIDATE_ONLY"
    assert dlr["full_loop_external_holdout_eligible"] is False
    assert "figure" in dlr["raw_data_status"]
    eho = next(
        item for item in record["candidates"]
        if item["id"] == "european_hydrogen_observatory_hrs_inventory_2026"
    )
    assert eho["admission_status"] == "INVENTORY_CONTEXT_ONLY"
    assert eho["full_loop_external_holdout_eligible"] is False
    kuroki = next(
        item for item in record["candidates"]
        if item["id"] == "kuroki_hrs_station_to_vehicle_model_2021"
    )
    assert kuroki["persistent_identifier"] == "10.1016/j.ijhydene.2021.04.037"
    assert kuroki["admission_status"] == "CONTACT_REQUEST_CANDIDATE_ONLY"
    assert kuroki["full_loop_external_holdout_eligible"] is False
    kuroki_thermal = next(
        item for item in record["candidates"]
        if item["id"] == "kuroki_hrs_liner_temperature_experiment_2023"
    )
    assert kuroki_thermal["persistent_identifier"] == "10.1002/ente.202300239"
    assert kuroki_thermal["admission_status"] == "CONTACT_REQUEST_CANDIDATE_ONLY"
    assert kuroki_thermal["full_loop_external_holdout_eligible"] is False
    assert "not_shared" in kuroki_thermal["raw_data_status"]
    nbsdc_station = next(
        item for item in record["candidates"]
        if item["id"] == "nbsdc_hydrogen_refuelling_station_operational_dataset_2023"
    )
    assert nbsdc_station["persistent_identifier"] == "CSTR 16666.11.nbsdc.aI3fJrzX"
    assert nbsdc_station["admission_status"] == "CONTACT_REQUEST_CANDIDATE_ONLY"
    assert nbsdc_station["full_loop_external_holdout_eligible"] is False
    nbsdc_vehicle = next(
        item for item in record["candidates"]
        if item["id"] == "nbsdc_hydrogen_fuel_cell_vehicle_operational_dataset_2023"
    )
    assert nbsdc_vehicle["persistent_identifier"] == "CSTR 16666.11.nbsdc.yxc5XLas"
    assert nbsdc_vehicle["admission_status"] == "CONTACT_REQUEST_CANDIDATE_ONLY"
    assert nbsdc_vehicle["full_loop_external_holdout_eligible"] is False
    nbsdc_liquid = next(
        item for item in record["candidates"]
        if item["id"] == "nbsdc_liquid_h2_station_runtime_2025"
    )
    assert nbsdc_liquid["admission_status"] == "CONTACT_REQUEST_CANDIDATE_ONLY"
    assert nbsdc_liquid["full_loop_external_holdout_eligible"] is False
    assert "application-required" in nbsdc_liquid["raw_data_status"]
    assert record["privacy"]["raw_rows_persisted"] is False


def test_candidate_leads_record_search_recheck_without_admitting_data() -> None:
    path = ROOT / "research/public_full_loop_candidate_leads_2026_10_10.json"
    record = json.loads(path.read_text(encoding="utf-8"))
    recheck = record["search_recheck"]
    assert recheck["checked_at"] == "2026-10-10"
    assert "synchronized" in recheck["finding"]
    assert "NBSDC" in " ".join(recheck["scope"])
    assert recheck["evidence_urls"]
    assert "Do not admit" in recheck["action"]


def test_nbsdc_liquid_access_recheck_is_metadata_only() -> None:
    path = ROOT / "research/nbsdc_liquid_h2_station_access_recheck_2026_10_10.json"
    record = json.loads(path.read_text(encoding="utf-8"))
    assert record["metadata_observed"]["listed_file_count"] == 7
    assert record["download_check"]["api_code"] == 403
    assert record["download_check"]["raw_rows_persisted"] is False
    assert record["admission"]["full_loop_external_holdout_eligible"] is False
