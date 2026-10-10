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
    assert record["privacy"]["raw_rows_persisted"] is False


def test_candidate_leads_record_search_recheck_without_admitting_data() -> None:
    path = ROOT / "research/public_full_loop_candidate_leads_2026_10_10.json"
    record = json.loads(path.read_text(encoding="utf-8"))
    recheck = record["search_recheck"]
    assert recheck["checked_at"] == "2026-10-10"
    assert "synchronized" in recheck["finding"]
    assert recheck["evidence_urls"]
    assert "Do not admit" in recheck["action"]
