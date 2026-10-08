import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _load(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def test_rheadhy_protocol_freezes_trace_evaluation_without_promoting_missing_data():
    protocol = _load(
        "research/rheadhy_public_test_matrix_pretrace_protocol_2026_10_08.json"
    )

    assert protocol["source"]["record_doi"] == "10.5281/zenodo.16992589"
    assert protocol["source"]["license"] == "CC BY 4.0"
    assert protocol["source"]["pdf_md5"] == "864e0cf8e55b00b62638015ca364803a"
    assert len(protocol["source"]["pdf_sha256"]) == 64
    assert protocol["verified_public_plan"]["planned_total_test_count"] == 300
    assert protocol["public_repository_recheck"][
        "machine_readable_test_result_dataset_found"
    ] is False
    assert protocol["known_before_freeze"]["aggregate_outcomes_already_public"] is True
    assert protocol["known_before_freeze"][
        "raw_time_series_or_case_level_numerical_outcomes_inspected"
    ] is False

    frozen = protocol["frozen_evaluation"]
    assert frozen["minimum_evaluable_cases"] >= 8
    assert frozen["minimum_joint_screen_pass_fraction"] >= 0.8
    assert len(frozen["required_channel_families"]) >= 12
    assert frozen["primary_screens"] == {
        "pressure_rmse_mpa_max": 5.0,
        "temperature_rmse_c_max": 10.0,
        "final_soc_absolute_error_percentage_points_max": 10.0,
    }

    eligibility = protocol["eligibility"]
    assert eligibility["trace_level_protocol_frozen"] is True
    assert eligibility["raw_synchronized_results_available"] is False
    assert eligibility["full_loop_external_validation_supported"] is False
    assert eligibility["goal_completion_permitted"] is False
    assert "protocol-integrity evidence only" in protocol["claim_boundary"]


def test_hyfill_is_not_ranked_as_full_loop_after_primary_source_recheck():
    priority = _load("research/validation_data_priority_refresh_2026_10_08.json")
    ranked = priority["ranked_candidates"]
    by_id = {row["id"]: row for row in ranked}

    assert ranked[0]["id"] == "rheadhy_2026_mid_flow_twin_campaign"
    hyfill = by_id["hyfill_hd_hrs_experiments_2026"]
    assert "full_loop_external_validation" not in hyfill["expected_gate_impact"]
    assert hyfill["eligibility"] == "component_tank_and_fuelling_line_only"
    assert hyfill["rank"] == len(ranked)
