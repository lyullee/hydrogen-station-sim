from h2station.llm_grounding import (
    build_evidence_manifest,
    prompt_decision_evidence,
    prompt_evidence_summary,
)


def test_llm_receives_data_availability_boundary_without_raw_rows():
    manifest = build_evidence_manifest(
        {"time_s": 0.0, "header_pressure_mpa": 45.0},
        {},
        [],
        False,
        question="공개 실측 데이터와 검증 범위를 설명해줘",
    )
    evidence = manifest["response_evidence"]["data_scarcity_validation_strategy"]
    assert evidence["local_inventory"]["deduplicated_rows"] == 56854143
    assert evidence["local_inventory"]["vehicle_side_channels_attested"] == 0
    assert evidence["public_evidence_role"][
        "rights_cleared_synchronized_full_loop_holdout_confirmed"
    ] is False
    assert evidence["minimum_next_request"]["pilot_event_count"] == 3
    assert evidence["minimum_next_request"]["raw_rows_committed"] is False

    summary = prompt_evidence_summary(manifest)["data_scarcity_validation_strategy"]
    assert summary["minimum_next_request"]["pilot_event_count"] == 3

    decision = prompt_decision_evidence(manifest)["decision_support_evidence"]
    strategy = decision["data_scarcity_validation_strategy"]
    assert strategy["station_side_actionable"] is True
    assert strategy["full_loop_holdout_confirmed"] is False
    assert strategy["required_channel_count"] == 6
    assert strategy["raw_rows_committed"] is False
