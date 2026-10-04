import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_cal_state_la_recheck_separates_real_provenance_from_raw_holdout():
    record = json.loads(
        (
            ROOT
            / "research/cal_state_la_hrff_public_data_recheck_2026_10_04.json"
        ).read_text(encoding="utf-8")
    )
    assert record["decision"] == (
        "HIGH_VALUE_REAL_HRS_CANDIDATES_NO_PUBLIC_RAW_LOGGER_FOUND"
    )
    assert record["gate_impact"] == "independent_full_loop_gate_remains_open"
    assert len(record["sources"]) == 3
    jclepro = next(
        item for item in record["sources"] if item["id"] == "calstate_jclepro_2021_back_to_back"
    )
    assert jclepro["real_world_provenance"] is True
    assert jclepro["public_artifact_inspection"]["raw_logger_file_found"] is False
    assert "flow rate" in jclepro["reported_scope"]["reported_dynamic_fields"]
    assert jclepro["full_loop_holdout_eligible"] is False
    assert record["recommended_next_step"]["freeze_rule"].startswith("Hash and quarantine")


def test_cal_state_la_recheck_has_a_prepared_request_draft():
    record = json.loads(
        (
            ROOT
            / "research/cal_state_la_hrff_public_data_recheck_2026_10_04.json"
        ).read_text(encoding="utf-8")
    )
    assert (
        ROOT / record["sources"][1]["request_draft"]
    ).exists()
