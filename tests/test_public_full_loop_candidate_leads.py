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
    nrel = next(item for item in record["candidates"] if item["id"].startswith("nrel_"))
    assert nrel["admission_status"] == "PARTIAL_STATION_TO_TANK_BOUNDARY_ONLY"
    assert nrel["full_loop_external_holdout_eligible"] is False
    assert record["privacy"]["raw_rows_persisted"] is False
